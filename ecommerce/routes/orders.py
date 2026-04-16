from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Product, ProductVariant, Order, OrderItem, Payment, PaymentStatus, OrderStatus
from datetime import datetime
import uuid
import json

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


# ── Email helper ──────────────────────────────────────────────────────────────

def send_order_status_email(order):
    """Fire-and-forget order status email to the buyer."""
    try:
        from flask_mail import Message as MailMessage
        from app import mail
        from flask import current_app
        buyer = order.buyer
        if not buyer or not buyer.email:
            return
        html = render_template(
            'email/order_status.html',
            username=buyer.username,
            order_number=order.order_number,
            status=order.status,
            total=order.total_amount,
            address=f"{order.delivery_address}, {order.delivery_city}",
            order_url=url_for('orders.order_detail', order_id=order.id, _external=True)
        )
        subject_map = {
            'pending':   'Order Received',
            'verified':  'Order Verified by Seller',
            'assigned':  'Rider Assigned to Your Order',
            'shipped':   'Your Order is Out for Delivery',
            'delivered': 'Your Order Has Been Delivered',
            'cancelled': 'Your Order Has Been Cancelled',
        }
        subject = f"Mode S7vn — {subject_map.get(order.status, 'Order Update')} ({order.order_number})"
        msg = MailMessage(subject, recipients=[buyer.email], html=html)
        mail.send(msg)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Order status email failed: {e}')


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

    for cart_key, qty in cart.items():
        pid, vid = _parse_cart_key(cart_key)
        product = Product.query.get(pid)
        if not product or not product.is_active:
            continue
        variant = ProductVariant.query.get(vid) if vid else None
        price   = variant.effective_price if variant else product.price
        subtotal = price * qty
        total   += subtotal
        cart_items.append({
            'cart_key': cart_key,
            'product': product,
            'variant': variant,
            'quantity': qty,
            'price': price,
            'subtotal': subtotal
        })

    return render_template('cart.html', cart_items=cart_items, total=total)


def _parse_cart_key(key):
    """Return (product_id, variant_id_or_None) from a cart key."""
    parts = str(key).split(':')
    pid = int(parts[0])
    vid = int(parts[1]) if len(parts) > 1 and parts[1] != '0' else None
    return pid, vid


@orders_bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product    = Product.query.get_or_404(product_id)
    quantity   = request.form.get('quantity', 1, type=int)
    variant_id = request.form.get('variant_id', type=int)

    if quantity < 1:
        quantity = 1

    # Require variant selection if product has variants
    if product.variants.count() > 0 and not variant_id:
        flash('Please select a size before adding to cart.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    if variant_id:
        variant = ProductVariant.query.get_or_404(variant_id)
        avail = variant.stock
    else:
        avail = product.stock

    if avail == 0:
        flash('This item is out of stock.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    if quantity > avail:
        flash(f'Only {avail} units available.', 'warning')
        quantity = avail

    cart = get_cart()

    # Enforce single-seller cart
    if cart:
        existing_key = next(iter(cart))
        existing_pid = int(existing_key.split(':')[0])
        existing_product = Product.query.get(existing_pid)
        if existing_product and existing_product.seller_id != product.seller_id:
            flash('Your cart contains items from a different seller. Clear your cart first.', 'warning')
            return redirect(url_for('products.view_product', product_id=product_id))

    cart_key = f"{product_id}:{variant_id or 0}"
    cart[cart_key] = cart.get(cart_key, 0) + quantity
    save_cart(cart)

    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('products.view_product', product_id=product_id))


@orders_bp.route('/remove-from-cart/<path:cart_key>', methods=['POST'])
def remove_from_cart(cart_key):
    cart = get_cart()
    cart.pop(cart_key, None)
    save_cart(cart)
    flash('Item removed from cart.', 'info')
    return redirect(url_for('orders.cart'))


@orders_bp.route('/update-cart/<path:cart_key>', methods=['POST'])
def update_cart(cart_key):
    quantity = request.form.get('quantity', 1, type=int)
    cart = get_cart()
    pid, vid = _parse_cart_key(cart_key)

    if quantity < 1:
        cart.pop(cart_key, None)
    else:
        if vid:
            variant = ProductVariant.query.get(vid)
            max_stock = variant.stock if variant else 0
        else:
            product = Product.query.get(pid)
            max_stock = product.stock if product else 0
        cart[cart_key] = min(quantity, max_stock)

    save_cart(cart)
    return redirect(url_for('orders.cart'))


# ── Checkout ──────────────────────────────────────────────────────────────────

@orders_bp.route('/buy-now/<int:product_id>', methods=['POST'])
@login_required
def buy_now(product_id):
    product    = Product.query.get_or_404(product_id)
    quantity   = request.form.get('quantity', 1, type=int)
    variant_id = request.form.get('variant_id', type=int)

    if quantity < 1:
        quantity = 1

    # If product has variants and none was selected, send back to product page
    variants = product.variants.all()
    if variants and not variant_id:
        flash('Please select a size before buying.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    if variant_id:
        variant = ProductVariant.query.get_or_404(variant_id)
        avail = variant.stock
    else:
        avail = product.stock

    if quantity > avail:
        flash(f'Only {avail} units available.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    session['buy_now_item'] = {'product_id': product_id, 'quantity': quantity, 'variant_id': variant_id}
    session.modified = True
    return redirect(url_for('orders.checkout', mode='buy_now'))


@orders_bp.route('/clear-cart', methods=['POST'])
def clear_cart():
    save_cart({})
    flash('Cart cleared.', 'info')
    return redirect(url_for('orders.cart'))


@orders_bp.route('/cancel-buy-now', methods=['POST'])
@login_required
def cancel_buy_now():
    """Discard buy-now item without touching the real cart."""
    session.pop('buy_now_item', None)
    session.modified = True
    return redirect(request.form.get('back_url') or url_for('products.list_products'))


@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    mode = request.args.get('mode', 'cart')

    def build_items(qty_overrides=None):
        items = []
        total = 0.0
        if mode == 'buy_now':
            bn = session.get('buy_now_item')
            if bn:
                product = Product.query.get(bn['product_id'])
                variant = ProductVariant.query.get(bn['variant_id']) if bn.get('variant_id') else None
                if product and product.is_active:
                    cart_key = f"{bn['product_id']}:{bn.get('variant_id') or 0}"
                    qty = qty_overrides.get(cart_key, bn['quantity']) if qty_overrides else bn['quantity']
                    avail = variant.stock if variant else product.stock
                    qty = max(1, min(int(qty), avail))
                    price = variant.effective_price if variant else product.price
                    subtotal = price * qty
                    total += subtotal
                    items.append({'product': product, 'variant': variant,
                                  'quantity': qty, 'price': price, 'subtotal': subtotal,
                                  'cart_key': cart_key})
        else:
            cart = get_cart()
            for cart_key, qty in cart.items():
                pid, vid = _parse_cart_key(cart_key)
                product = Product.query.get(pid)
                variant = ProductVariant.query.get(vid) if vid else None
                if product and product.is_active:
                    qty = qty_overrides.get(cart_key, qty) if qty_overrides else qty
                    avail = variant.stock if variant else product.stock
                    qty = max(1, min(int(qty), avail))
                    price = variant.effective_price if variant else product.price
                    subtotal = price * qty
                    total += subtotal
                    items.append({'product': product, 'variant': variant,
                                  'quantity': qty, 'price': price, 'subtotal': subtotal,
                                  'cart_key': cart_key})
        return items, round(total, 2)

    if mode == 'buy_now' and not session.get('buy_now_item'):
        flash('Nothing to checkout.', 'warning')
        return redirect(url_for('products.list_products'))
    if mode == 'cart' and not get_cart():
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('orders.cart'))

    if request.method == 'POST':
        qty_overrides = {}
        for key, val in request.form.items():
            if key.startswith('qty_'):
                try:
                    qty_overrides[key[4:]] = int(val)
                except ValueError:
                    pass

        cart_items, total = build_items(qty_overrides)
        if not cart_items:
            flash('No valid items.', 'warning')
            return redirect(url_for('orders.cart'))

        delivery_address = request.form.get('delivery_address', '').strip()
        delivery_city    = request.form.get('delivery_city', '').strip()
        delivery_zip     = request.form.get('delivery_zip', '').strip()

        if not delivery_address or not delivery_city:
            flash('Delivery address and city are required.', 'danger')
            return render_template('checkout.html', cart_items=cart_items, total=total, mode=mode)

        seller_id = cart_items[0]['product'].seller_id
        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            buyer_id=current_user.id,
            seller_id=seller_id,
            delivery_address=delivery_address,
            delivery_city=delivery_city,
            delivery_zip=delivery_zip,
            total_amount=total,
            status=OrderStatus.PENDING.value
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            product = item['product']
            variant = item['variant']
            qty     = item['quantity']

            # Variant-level stock deduction
            if variant:
                if variant.stock < qty:
                    db.session.rollback()
                    flash(f'Not enough stock for {product.name} ({variant.size}{("/" + variant.color) if variant.color else ""}).', 'danger')
                    return render_template('checkout.html', cart_items=cart_items, total=total, mode=mode)
                variant.stock -= qty
                # Keep parent stock in sync
                product.stock = max(0, product.stock - qty)
            else:
                if product.stock < qty:
                    db.session.rollback()
                    flash(f'Not enough stock for {product.name}.', 'danger')
                    return render_template('checkout.html', cart_items=cart_items, total=total, mode=mode)
                product.stock -= qty

            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id if variant else None,
                quantity=qty,
                price=item['price'],
                subtotal=item['subtotal'],
                variant_size=variant.size if variant else None,
                variant_color=variant.color if variant else None,
            ))

        db.session.add(Payment(
            order_id=order.id,
            amount=total,
            method='cod',
            status=PaymentStatus.PENDING.value
        ))
        db.session.commit()

        if mode == 'buy_now':
            session.pop('buy_now_item', None)
        else:
            save_cart({})

        send_order_status_email(order)
        flash('Order placed! Waiting for seller to verify.', 'success')
        return redirect(url_for('orders.order_detail', order_id=order.id))

    cart_items, total = build_items()
    return render_template('checkout.html', cart_items=cart_items, total=total, mode=mode)


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
    return redirect(url_for('products.seller_orders'))


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
    send_order_status_email(order)
    flash(f'Order {order.order_number} verified! Ready to assign a rider.', 'success')
    return redirect(url_for('products.seller_orders'))


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

    # Restore stock at variant level
    for item in order.items:
        if item.variant_id and item.variant:
            item.variant.stock += item.quantity
            item.product.stock = min(item.product.stock + item.quantity,
                                     sum(v.stock for v in item.product.variants.all()))
        else:
            item.product.stock += item.quantity

    order.status = OrderStatus.CANCELLED.value
    db.session.commit()
    send_order_status_email(order)
    flash(f'Order {order.order_number} cancelled.', 'info')

    if current_user.is_seller():
        return redirect(url_for('products.seller_orders'))
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
    send_order_status_email(order)
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
    send_order_status_email(order)
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
    send_order_status_email(order)
    flash('Order status updated.', 'success')
    return redirect(url_for('orders.order_detail', order_id=order_id))
