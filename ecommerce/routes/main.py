from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from models import Order, OrderStatus

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return render_template('index.html')

    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))

    if current_user.is_seller():
        return redirect(url_for('products.seller_dashboard'))

    if current_user.is_rider():
        active_orders = Order.query.filter(
            Order.rider_id == current_user.id,
            Order.status.in_([OrderStatus.ASSIGNED.value, OrderStatus.SHIPPED.value])
        ).order_by(Order.created_at.desc()).all()

        completed = Order.query.filter_by(
            rider_id=current_user.id,
            status=OrderStatus.DELIVERED.value
        ).count()

        return render_template('rider_dashboard.html',
                               active_orders=active_orders,
                               completed=completed)

    all_orders = Order.query.filter_by(buyer_id=current_user.id)
    stats = {
        'total': all_orders.count(),
        'pending': all_orders.filter_by(status=OrderStatus.PENDING.value).count(),
        'active': all_orders.filter(
            Order.status.in_([OrderStatus.VERIFIED.value, OrderStatus.ASSIGNED.value, OrderStatus.SHIPPED.value])
        ).count(),
        'delivered': all_orders.filter_by(status=OrderStatus.DELIVERED.value).count()
    }
    return render_template('buyer_dashboard.html', stats=stats)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')
