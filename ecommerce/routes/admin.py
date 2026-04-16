from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Product, Order, OrderItem, Payment, UserRole, OrderStatus
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to check if user is admin"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required!', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    
    stats = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active   = request.form.get('is_active') == 'on'
    user.is_verified = request.form.get('is_verified') == 'on'
    db.session.commit()
    action = 'approved' if user.is_active else 'deactivated'
    flash(f'User {user.username} {action}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/products')
@login_required
@admin_required
def manage_products():
    """Manage products"""
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(page=page, per_page=20)
    return render_template('admin/products.html', products=products)

@admin_bp.route('/products/<int:product_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_product(product_id):
    """Toggle product active status"""
    product = Product.query.get_or_404(product_id)
    product.is_active = not product.is_active
    db.session.commit()
    flash('Product status updated!', 'success')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/orders/<int:order_id>/assign-rider', methods=['POST'])
@login_required
@admin_required
def assign_rider(order_id):
    """Assign a rider to a verified order."""
    order = Order.query.get_or_404(order_id)

    if order.status != OrderStatus.VERIFIED.value:
        flash('Only verified orders can be assigned a rider.', 'warning')
        return redirect(url_for('admin.manage_orders'))

    rider_id = request.form.get('rider_id', type=int)
    rider = User.query.filter_by(id=rider_id, role=UserRole.RIDER.value, is_active=True).first()

    if not rider:
        flash('Invalid rider selected.', 'danger')
        return redirect(url_for('admin.manage_orders'))

    order.rider_id = rider.id
    order.status = OrderStatus.ASSIGNED.value
    db.session.commit()
    flash(f'Rider {rider.username} assigned to order {order.order_number}.', 'success')
    return redirect(url_for('admin.manage_orders'))


@admin_bp.route('/orders')
@login_required
@admin_required
def manage_orders():
    """Manage orders"""
    page = request.args.get('page', 1, type=int)
    orders = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20)
    riders = User.query.filter_by(role=UserRole.RIDER.value, is_active=True).all()
    return render_template('admin/orders.html', orders=orders, riders=riders)

@admin_bp.route('/sellers')
@login_required
@admin_required
def manage_sellers():
    """Manage sellers"""
    page = request.args.get('page', 1, type=int)
    sellers = User.query.filter_by(role=UserRole.SELLER.value).paginate(page=page, per_page=20)
    return render_template('admin/sellers.html', sellers=sellers)

@admin_bp.route('/riders')
@login_required
@admin_required
def manage_riders():
    """Manage riders"""
    page = request.args.get('page', 1, type=int)
    riders = User.query.filter_by(role=UserRole.RIDER.value).paginate(page=page, per_page=20)
    return render_template('admin/riders.html', riders=riders)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    from sqlalchemy import func
    from models import OrderStatus

    # Revenue from delivered orders only
    revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(status=OrderStatus.DELIVERED.value).scalar() or 0

    # Orders by status
    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status).all()
    )

    # Users by role
    role_counts = dict(
        db.session.query(User.role, func.count(User.id))
        .group_by(User.role).all()
    )

    # Top 5 products by units sold
    from models import OrderItem, Product
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('units')
    ).join(OrderItem).group_by(Product.id)\
     .order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    return render_template('admin/reports.html',
                           revenue=revenue,
                           status_counts=status_counts,
                           role_counts=role_counts,
                           top_products=top_products)
