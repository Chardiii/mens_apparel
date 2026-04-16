from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Product, Order, OrderItem, Payment, PaymentStatus, OrderStatus
from datetime import datetime
import uuid
import json

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


# ── Cart helpers ──────────────────────────────────────────────────────────────

def get_cart():
    return session.get('cart', {})  # {product_id_str: quantity}

def save_cart(cart):
    session['cart'] = cart
    session.modified = True


# ── Cart routes ───────────────────────────────────────────────────────────────

@orders_bp.route('/cart')
def cart():
    cart = get_cart()
    cart_items = []
    total = 0.0

    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product and product.is_active:
            subtotal = product.price * qty
            total += subtotal
            cart_items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})

    return render_template('cart.html', cart_items=cart_items, total=total)


@orders_bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = request.form.get('quantity', 1, type=int)

    if quantity < 1:
        quantity = 1
    if quantity > product.stock:
        flash(f'Only {product.stock} units available.', 'warning')
        quantity = product.stock

    cart = get_cart()

    # Enforce single-seller cart
    if cart:
        existing_pid = next(iter(cart))
        existing_product = Product.query.get(int(existing_pid))
        if existing_product and existing_product.seller_id != product.seller_id:
            flash('Your cart contains items from a different seller. Clear your cart first to add this item.', 'warning')
            return redirect(url_for('products.view_product', product_id=product_id))

    pid_str = str(product_id)
    cart[pid_str] = cart.get(pid_str, 0) + quantity
    save_cart(cart)

    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('products.view_product', product_id=product_id))


@orders_bp.route('/remove-from-cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    save_cart(cart)
    flash('Item removed from cart.', 'info')
    return redirect(url_for('orders.cart'))


@orders_bp.route('/update-cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    quantity = request.form.get('quantity', 1, type=int)
    cart = get_cart()
    pid_str = str(product_id)

    if quantity < 1:
        cart.pop(pid_str, None)
    else:
        product = Product.query.get_or_404(product_id)
        cart[pid_str] = min(quantity, product.stock)

    save_cart(cart)
    return redirect(url_for('orders.cart'))


# ── Checkout ──────────────────────────────────────────────────────────────────

@orders_bp.route('/clear-cart', methods=['POST'])
def clear_cart():
    save_cart({})
    flash('Cart cleared.', 'info')
    return redirect(url_for('orders.cart'))


@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('orders.cart'))

    # Build cart preview for GET and validation
    cart_items = []
    total = 0.0
    for pid_str, qty in cart.items():
        product = Product.query.get(int(pid_str))
        if product and product.is_active:
            subtotal = product.price * qty
            total += subtotal
            cart_items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})

    if not cart_items:
        flash('No valid items in cart.', 'warning')
        return redirect(url_for('orders.cart'))

    if request.method == 'POST':
        delivery_address = request.form.get('delivery_address', '').strip()
        delivery_city = request.form.get('delivery_city', '').strip()
        delivery_zip = request.form.get('delivery_zip', '').strip()

        if not delivery_address or not delivery_city:
            flash('Delivery address and city are required.', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total)

        # Determine seller — use first item's seller (single-seller order for now)
        seller_id = cart_items[0]['product'].seller_id

        # Create order
        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            buyer_id=current_user.id,
            seller_id=seller_id,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_zip=delivery_zip,
            total_amount=round(total, 2),
            status=OrderStatus.PENDING.value
        )
        db.session.add(order)
        db.session.flush()

        # Create order items & deduct stock
        for item in cart_items:
            product = item['product']
            qty = item['quantity']
            if product.stock < qty:
                db.session.rollback()
                flash(f'Not enough stock for {product.name}.', 'danger')
                return render_template('checkout.html', cart_items=cart_items, total=total)

            product.stock -= qty
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                price=product.price,
                subtotal=round(product.price * qty, 2)
            ))

        # COD payment record
        db.session.add(Payment(
            order_id=order.id,
            amount=round(total, 2),
            method='cod',
            status=PaymentStatus.PENDING.value
        ))

        db.session.commit()
        save_cart({})  # Clear cart

        flash('Order placed! Waiting for seller to verify.', 'success')
        return redirect(url_for('orders.order_detail', order_id=order.id))

    return render_template('checkout.html', cart_items=cart_items, total=total)


# ── Order views ───────────────────────────────────────────────────────────────

@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)

    is_buyer = order.buyer_id == current_user.id
    is_seller = order.seller_id == current_user.id
    is_rider = order.rider_id == current_user.id

    if not (is_buyer or is_seller or is_rider or current_user.is_admin()):
        flash('Not authorized to view this order.', 'danger')
        return redirect(url_for('main.index'))

    return render_template('order_detail.html', order=order)


@orders_bp.route('/my-orders')
@login_required
def my_orders():
    if not current_user.is_buyer():
        flash('Only buyers can view their orders.', 'danger')
        return redirect(url_for('main.index'))

    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('my_orders.html', orders=orders)


# ── Seller order management ───────────────────────────────────────────────────

@orders_bp.route('/seller/received')
@login_required
def seller_received_orders():
    if not current_user.is_seller():
        flash('Only sellers can view this.', 'danger')
        return redirect(url_for('main.index'))

    orders = Order.query.filter_by(seller_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    return render_template('seller_orders.html', orders=orders)


@orders_bp.route('/<int:order_id>/verify', methods=['POST'])
@login_required
def verify_order(order_id):
    """Seller verifies the order and marks it ready for rider pickup."""
    if not current_user.is_seller():
        flash('Only sellers can verify orders.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)

    if order.seller_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('orders.seller_received_orders'))

    if order.status != OrderStatus.PENDING.value:
        flash('Only pending orders can be verified.', 'warning')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    order.status = OrderStatus.VERIFIED.value
    db.session.commit()
    flash(f'Order {order.order_number} verified! Ready to assign a rider.', 'success')
    return redirect(url_for('orders.seller_received_orders'))


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Seller or buyer can cancel a pending order."""
    order = Order.query.get_or_404(order_id)

    is_buyer = order.buyer_id == current_user.id and order.status == OrderStatus.PENDING.value
    is_seller = order.seller_id == current_user.id and order.status in [OrderStatus.PENDING.value, OrderStatus.VERIFIED.value]

    if not (is_buyer or is_seller or current_user.is_admin()):
        flash('Not authorized to cancel this order.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    # Restore stock
    for item in order.items:
        item.product.stock += item.quantity

    order.status = OrderStatus.CANCELLED.value
    db.session.commit()
    flash(f'Order {order.order_number} cancelled.', 'info')

    if current_user.is_seller():
        return redirect(url_for('orders.seller_received_orders'))
    return redirect(url_for('orders.my_orders'))


# ── Rider delivery actions ────────────────────────────────────────────────────

@orders_bp.route('/<int:order_id>/pickup', methods=['POST'])
@login_required
def pickup_order(order_id):
    """Rider marks order as picked up (shipped)."""
    if not current_user.is_rider():
        flash('Only riders can mark pickups.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)

    if order.rider_id != current_user.id:
        flash('This order is not assigned to you.', 'danger')
        return redirect(url_for('main.dashboard'))

    if order.status != OrderStatus.ASSIGNED.value:
        flash('Order must be assigned before pickup.', 'warning')
        return redirect(url_for('main.dashboard'))

    order.status = OrderStatus.SHIPPED.value
    db.session.commit()
    flash(f'Order {order.order_number} marked as picked up.', 'success')
    return redirect(url_for('main.dashboard'))


@orders_bp.route('/<int:order_id>/deliver', methods=['POST'])
@login_required
def deliver_order(order_id):
    """Rider marks order as delivered and cash collected."""
    if not current_user.is_rider():
        flash('Only riders can mark deliveries.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)

    if order.rider_id != current_user.id:
        flash('This order is not assigned to you.', 'danger')
        return redirect(url_for('main.dashboard'))

    if order.status != OrderStatus.SHIPPED.value:
        flash('Order must be picked up before marking delivered.', 'warning')
        return redirect(url_for('main.dashboard'))

    order.status = OrderStatus.DELIVERED.value
    order.delivered_at = datetime.utcnow()

    if order.payment:
        order.payment.status = 'collected'

    db.session.commit()
    flash(f'Order {order.order_number} delivered! Cash collected.', 'success')
    return redirect(url_for('main.dashboard'))


# ── Admin status update ───────────────────────────────────────────────────────

@orders_bp.route('/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_order_status(order_id):
    """Admin-only status update."""
    if not current_user.is_admin():
        flash('Admin access required.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    valid = [s.value for s in OrderStatus]

    if new_status not in valid:
        flash('Invalid status.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    order.status = new_status
    if new_status == OrderStatus.DELIVERED.value:
        order.delivered_at = datetime.utcnow()

    db.session.commit()
    flash('Order status updated.', 'success')
    return redirect(url_for('orders.order_detail', order_id=order_id))
