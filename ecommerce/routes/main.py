from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from models import Order, OrderStatus, Product
from routes.products import CATEGORIES

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    featured = Product.query.filter_by(is_active=True)\
        .order_by(Product.rating.desc(), Product.review_count.desc())\
        .limit(8).all()
    return render_template('index.html', featured=featured, categories=CATEGORIES)

@main_bp.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return render_template('index.html')

    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))

    if current_user.is_seller():
        return redirect(url_for('products.seller_dashboard'))

    if current_user.is_rider():
        from sqlalchemy import func
        from models import db

        active_orders = Order.query.filter(
            Order.rider_id == current_user.id,
            Order.status.in_([OrderStatus.ASSIGNED.value, OrderStatus.SHIPPED.value])
        ).order_by(Order.created_at.desc()).all()

        delivered_orders = Order.query.filter_by(
            rider_id=current_user.id,
            status=OrderStatus.DELIVERED.value
        ).order_by(Order.delivered_at.desc()).all()

        completed   = len(delivered_orders)
        earnings    = sum(o.total_amount for o in delivered_orders)

        # This week vs last week
        from datetime import date, timedelta
        today     = date.today()
        week_ago  = today - timedelta(days=7)
        this_week = sum(
            o.total_amount for o in delivered_orders
            if o.delivered_at and o.delivered_at.date() >= week_ago
        )

        return render_template('rider_dashboard.html',
                               active_orders=active_orders,
                               delivered_orders=delivered_orders[:20],
                               completed=completed,
                               earnings=round(earnings, 2),
                               this_week=round(this_week, 2))

    all_orders = Order.query.filter_by(buyer_id=current_user.id)
    # Buyers go to index, not a separate dashboard
    return redirect(url_for('main.index'))

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    return render_template('contact.html')
