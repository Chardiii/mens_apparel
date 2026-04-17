from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Product, ProductVariant, Order, OrderItem, Payment, PaymentStatus, OrderStatus, CartItem
from datetime import datetime
import uuid

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
            'pending':          'Order Received',
            'verified':         'Order Verified by Seller',
            'assigned':         'Rider Assigned to Your Order',
            'shipped':          'Your Order is Out for Delivery',
            'delivered':        'Your Order Has Been Delivered',
            'cancelled':        'Your Order Has Been Cancelled',
            'cancel_requested': 'Cancellation Request Received',
        }
        subject = f"Mode S7vn — {subject_map.get(order.status, 'Order Update')} ({order.order_number})"
        msg = MailMessage(subject, recipients=[buyer.email], html=html)
        mail.send(msg)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Order status email failed: {e}')


# ── Cart helpers ──────────────────────────────────────────────────────────────

def _parse_cart_key(key):
    parts = str(key).split(':')
    pid = int(parts[0])
    vid = int(parts[1]) if len(parts) > 1 and parts[1] != '0' else None
    return pid, vid


def _db_cart_items(user_id):
    """Return CartItem rows for a user, skipping inactive/deleted products."""
    return [
        item for item in
        CartItem.query.filter_by(user_id=user_id)
                      .order_by(CartItem.added_at.asc()).all()
        if item.product and item.product.is_active
    ]


def _session_cart_items():
    """Return cart-item dicts from the session (guest users)."""
    raw = session.get('cart', {})
    items = []
    for cart_key, qty in raw.items():
        pid, vid = _parse_cart_key(cart_key)
        product = Product.query.get(pid)
        if not product or not product.is_active:
            continue
        variant = ProductVariant.query.get(vid) if vid else None
        items.append({'cart_key': cart_key, 'product': product,
                      'variant': variant, 'quantity': qty})
    return items


def merge_session_cart_to_db(user_id):
    """Called on login: move any session cart items into the DB cart."""
    raw = session.pop('cart', {})
    if not raw:
        return
    for cart_key, qty in raw.items():
        pid, vid = _parse_cart_key(cart_key)
        product = Product.query.get(pid)
        if not product or not product.is_active:
            continue
        existing = CartItem.query.filter_by(
            user_id=user_id, product_id=pid, variant_id=vid
        ).first()
        if existing:
            avail = existing.variant.stock if existing.variant else existing.product.stock
            existing.quantity = min(existing.quantity + qty, avail)
        else:
            variant = ProductVariant.query.get(vid) if vid else None
            avail = variant.stock if variant else product.stock
            db.session.add(CartItem(
                user_id=user_id, product_id=pid,
                variant_id=vid, quantity=min(qty, avail)
            ))
    db.session.commit()
    session.modified = True


def get_cart_count():
    """Total item count for the navbar badge."""
    if current_user.is_authenticated:
        return db.session.query(
            db.func.sum(CartItem.quantity)
        ).filter_by(user_id=current_user.id).scalar() or 0
    return sum(session.get('cart', {}).values())


# ── Cart routes ───────────────────────────────────────────────────────────────

@orders_bp.route('/cart')
def cart():
    if current_user.is_authenticated:
        rows = _db_cart_items(current_user.id)
        cart_items = [{
            'cart_key': r.cart_key,
            'product':  r.product,
            'variant':  r.variant,
            'quantity': r.quantity,
            'price':    r.price,
            'subtotal': r.subtotal,
        } for r in rows]
    else:
        cart_items = []
        for item in _session_cart_items():
            price    = item['variant'].effective_price if item['variant'] else item['product'].price
            subtotal = round(price * item['quantity'], 2)
            cart_items.append({**item, 'price': price, 'subtotal': subtotal})

    total = round(sum(i['subtotal'] for i in cart_items), 2)
    return render_template('cart.html', cart_items=cart_items, total=total)


@orders_bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product    = Product.query.get_or_404(product_id)
    quantity   = request.form.get('quantity', 1, type=int)
    variant_id = request.form.get('variant_id', type=int)

    if quantity < 1:
        quantity = 1

    if product.variants.count() > 0 and not variant_id:
        flash('Please select a size before adding to cart.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    variant = ProductVariant.query.get(variant_id) if variant_id else None
    avail   = variant.stock if variant else product.stock

    if avail == 0:
        flash('This item is out of stock.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    quantity = min(quantity, avail)

    if current_user.is_authenticated:
        # Enforce single-seller cart
        first = CartItem.query.filter_by(user_id=current_user.id).first()
        if first and first.product.seller_id != product.seller_id:
            flash('Your cart contains items from a different seller. Clear your cart first.', 'warning')
            return redirect(url_for('products.view_product', product_id=product_id))

        existing = CartItem.query.filter_by(
            user_id=current_user.id, product_id=product_id, variant_id=variant_id
        ).first()
        if existing:
            existing.quantity = min(existing.quantity + quantity, avail)
        else:
            db.session.add(CartItem(
                user_id=current_user.id, product_id=product_id,
                variant_id=variant_id, quantity=quantity
            ))
        db.session.commit()
    else:
        # Guest: session cart
        cart = session.get('cart', {})
        if cart:
            existing_key = next(iter(cart))
            existing_pid = int(existing_key.split(':')[0])
            existing_product = Product.query.get(existing_pid)
            if existing_product and existing_product.seller_id != product.seller_id:
                flash('Your cart contains items from a different seller. Clear your cart first.', 'warning')
                return redirect(url_for('products.view_product', product_id=product_id))
        key = f"{product_id}:{variant_id or 0}"
        cart[key] = min(cart.get(key, 0) + quantity, avail)
        session['cart'] = cart
        session.modified = True

    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('products.view_product', product_id=product_id))


@orders_bp.route('/remove-from-cart/<path:cart_key>', methods=['POST'])
def remove_from_cart(cart_key):
    if current_user.is_authenticated:
        pid, vid = _parse_cart_key(cart_key)
        CartItem.query.filter_by(
            user_id=current_user.id, product_id=pid, variant_id=vid
        ).delete()
        db.session.commit()
    else:
        cart = session.get('cart', {})
        cart.pop(cart_key, None)
        session['cart'] = cart
        session.modified = True
    flash('Item removed from cart.', 'info')
    return redirect(url_for('orders.cart'))


@orders_bp.route('/update-cart/<path:cart_key>', methods=['POST'])
def update_cart(cart_key):
    quantity = request.form.get('quantity', 1, type=int)
    pid, vid = _parse_cart_key(cart_key)

    variant = ProductVariant.query.get(vid) if vid else None
    product = Product.query.get(pid)
    max_stock = (variant.stock if variant else product.stock) if product else 0

    if current_user.is_authenticated:
        item = CartItem.query.filter_by(
            user_id=current_user.id, product_id=pid, variant_id=vid
        ).first()
        if item:
            if quantity < 1:
                db.session.delete(item)
            else:
                item.quantity = min(quantity, max_stock)
            db.session.commit()
    else:
        cart = session.get('cart', {})
        if quantity < 1:
            cart.pop(cart_key, None)
        else:
            cart[cart_key] = min(quantity, max_stock)
        session['cart'] = cart
        session.modified = True

    return redirect(url_for('orders.cart'))


@orders_bp.route('/clear-cart', methods=['POST'])
def clear_cart():
    if current_user.is_authenticated:
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    else:
        session.pop('cart', None)
        session.modified = True
    flash('Cart cleared.', 'info')
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
            rows = _db_cart_items(current_user.id)
            for row in rows:
                cart_key = row.cart_key
                qty = qty_overrides.get(cart_key, row.quantity) if qty_overrides else row.quantity
                avail = row.variant.stock if row.variant else row.product.stock
                qty = max(1, min(int(qty), avail))
                price = row.variant.effective_price if row.variant else row.product.price
                subtotal = round(price * qty, 2)
                total += subtotal
                items.append({'product': row.product, 'variant': row.variant,
                              'quantity': qty, 'price': price, 'subtotal': subtotal,
                              'cart_key': cart_key})
        return items, round(total, 2)

    if mode == 'buy_now' and not session.get('buy_now_item'):
        flash('Nothing to checkout.', 'warning')
        return redirect(url_for('products.list_products'))
    if mode == 'cart' and not _db_cart_items(current_user.id):
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
            CartItem.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()

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
    """Buyer requests cancellation or seller directly cancels."""
    order = Order.query.get_or_404(order_id)
    reason = request.form.get('cancel_reason', '').strip()

    is_buyer = order.buyer_id == current_user.id
    is_seller = order.seller_id == current_user.id

    if not (is_buyer or is_seller or current_user.is_admin()):
        flash('Not authorized to cancel this order.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    # Buyer cannot cancel if order is already shipped, assigned, or delivered
    if is_buyer and order.status in [OrderStatus.SHIPPED.value, OrderStatus.ASSIGNED.value, OrderStatus.DELIVERED.value]:
        flash('Cannot cancel order — it is already out for delivery or delivered.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    # Buyer requests cancellation (needs seller approval)
    if is_buyer and order.status in [OrderStatus.PENDING.value, OrderStatus.VERIFIED.value]:
        if not reason:
            flash('Please provide a reason for cancellation.', 'warning')
            return redirect(url_for('orders.order_detail', order_id=order_id))
        order.status = OrderStatus.CANCEL_REQUESTED.value
        order.cancel_reason = reason
        order.cancel_requested_by = 'buyer'
        order.cancel_status = 'pending'
        db.session.commit()
        flash(f'Cancellation request submitted. Waiting for seller approval.', 'info')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    # Seller directly cancels (immediate, no approval needed)
    if is_seller and order.status in [OrderStatus.PENDING.value, OrderStatus.VERIFIED.value]:
        if not reason:
            reason = 'Cancelled by seller'
        _restore_stock(order)
        order.status = OrderStatus.CANCELLED.value
        order.cancel_reason = reason
        order.cancel_requested_by = 'seller'
        order.cancel_status = 'approved'
        db.session.commit()
        send_order_status_email(order)
        flash(f'Order {order.order_number} cancelled. Stock restored.', 'info')
        return redirect(url_for('products.seller_orders'))

    # Admin can cancel anytime
    if current_user.is_admin():
        _restore_stock(order)
        order.status = OrderStatus.CANCELLED.value
        order.cancel_reason = reason or 'Cancelled by admin'
        order.cancel_requested_by = 'admin'
        order.cancel_status = 'approved'
        db.session.commit()
        send_order_status_email(order)
        flash(f'Order {order.order_number} cancelled. Stock restored.', 'info')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    flash('Cannot cancel this order at this stage.', 'warning')
    return redirect(url_for('orders.order_detail', order_id=order_id))


@orders_bp.route('/<int:order_id>/approve-cancel', methods=['POST'])
@login_required
def approve_cancel(order_id):
    """Seller approves buyer's cancellation request."""
    if not current_user.is_seller():
        flash('Only sellers can approve cancellations.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)

    if order.seller_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('products.seller_orders'))

    if order.status != OrderStatus.CANCEL_REQUESTED.value:
        flash('No pending cancellation request.', 'warning')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    _restore_stock(order)
    order.status = OrderStatus.CANCELLED.value
    order.cancel_status = 'approved'
    db.session.commit()
    _send_cancel_decision_email(order, approved=True)
    flash(f'Cancellation approved. Stock restored for order {order.order_number}.', 'success')
    return redirect(url_for('products.seller_orders'))


@orders_bp.route('/<int:order_id>/reject-cancel', methods=['POST'])
@login_required
def reject_cancel(order_id):
    """Seller rejects buyer's cancellation request."""
    if not current_user.is_seller():
        flash('Only sellers can reject cancellations.', 'danger')
        return redirect(url_for('main.index'))

    order = Order.query.get_or_404(order_id)

    if order.seller_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('products.seller_orders'))

    if order.status != OrderStatus.CANCEL_REQUESTED.value:
        flash('No pending cancellation request.', 'warning')
        return redirect(url_for('orders.order_detail', order_id=order_id))

    rejection_reason = request.form.get('rejection_reason', '').strip()
    order.status = OrderStatus.PENDING.value
    order.cancel_status = 'rejected'
    db.session.commit()
    _send_cancel_decision_email(order, approved=False, rejection_reason=rejection_reason)
    flash(f'Cancellation request rejected for order {order.order_number}.', 'info')
    return redirect(url_for('products.seller_orders'))


def _send_cancel_decision_email(order, approved, rejection_reason=''):
    """Email the buyer when seller approves or rejects their cancel request."""
    try:
        from flask_mail import Message as MailMessage
        from app import mail
        buyer = order.buyer
        if not buyer or not buyer.email:
            return
        html = render_template(
            'email/cancel_decision.html',
            username=buyer.username,
            order_number=order.order_number,
            total=order.total_amount,
            approved=approved,
            cancel_reason=order.cancel_reason,
            rejection_reason=rejection_reason,
            order_url=url_for('orders.order_detail', order_id=order.id, _external=True)
        )
        subject = (
            f"Mode S7vn — Cancellation Approved ({order.order_number})"
            if approved else
            f"Mode S7vn — Cancellation Request Rejected ({order.order_number})"
        )
        msg = MailMessage(subject, recipients=[buyer.email], html=html)
        mail.send(msg)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'Cancel decision email failed: {e}')


def _restore_stock(order):
    """Restore stock for all items in the order at variant level."""
    for item in order.items:
        if item.variant_id and item.variant:
            item.variant.stock += item.quantity
            # Sync parent stock: sum all variant stocks
            item.product.stock = sum(v.stock for v in item.product.variants.all())
        else:
            item.product.stock += item.quantity


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
