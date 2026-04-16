from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
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
    from datetime import date, timedelta

    # Core counts
    total_users     = User.query.count()
    total_products  = Product.query.count()
    total_orders    = Order.query.count()
    pending_users   = User.query.filter_by(is_active=False, is_banned=False).count()
    pending_sellers = User.query.filter_by(role=UserRole.SELLER.value, is_active=False).count()
    pending_riders  = User.query.filter_by(role=UserRole.RIDER.value,  is_active=False).count()
    active_deliveries = Order.query.filter(
        Order.status.in_([OrderStatus.ASSIGNED.value, OrderStatus.SHIPPED.value])
    ).count()
    verified_orders = Order.query.filter_by(status=OrderStatus.VERIFIED.value).count()

    # Revenue
    gmv = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(status=OrderStatus.DELIVERED.value).scalar() or 0

    # Active users by role
    from sqlalchemy import case
    role_active = dict(
        db.session.query(User.role, func.count(User.id))
        .filter_by(is_active=True)
        .group_by(User.role).all()
    )

    # 7-day revenue chart
    today = date.today()
    chart_labels = []
    chart_revenue = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_rev = db.session.query(func.sum(Order.total_amount)).filter(
            Order.status == OrderStatus.DELIVERED.value,
            func.date(Order.delivered_at) == day
        ).scalar() or 0
        chart_labels.append(day.strftime('%b %d'))
        chart_revenue.append(round(float(day_rev), 2))

    # 7-day new users chart
    chart_users = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = User.query.filter(func.date(User.created_at) == day).count()
        chart_users.append(count)

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    stats = {
        'total_users':      total_users,
        'total_products':   total_products,
        'total_orders':     total_orders,
        'gmv':              round(float(gmv), 2),
        'revenue':          round(float(revenue), 2),
        'pending_users':    pending_users,
        'pending_sellers':  pending_sellers,
        'pending_riders':   pending_riders,
        'active_deliveries':active_deliveries,
        'verified_orders':  verified_orders,
        'role_active':      role_active,
    }
    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_orders=recent_orders,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           chart_users=chart_users)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    page        = request.args.get('page', 1, type=int)
    filter_role = request.args.get('role', '')       # buyer|seller|rider|''
    filter_status = request.args.get('status', '')   # pending|banned|active|''

    query = User.query
    if filter_role:
        query = query.filter_by(role=filter_role)
    if filter_status == 'pending':
        query = query.filter_by(is_active=False, is_banned=False)
    elif filter_status == 'banned':
        query = query.filter_by(is_banned=True)
    elif filter_status == 'active':
        query = query.filter_by(is_active=True, is_banned=False)

    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)

    counts = {
        'all':     User.query.count(),
        'pending': User.query.filter_by(is_active=False, is_banned=False).count(),
        'active':  User.query.filter_by(is_active=True,  is_banned=False).count(),
        'banned':  User.query.filter_by(is_banned=True).count(),
        'buyer':   User.query.filter_by(role='buyer').count(),
        'seller':  User.query.filter_by(role='seller').count(),
        'rider':   User.query.filter_by(role='rider').count(),
    }
    return render_template('admin/users.html', users=users, counts=counts,
                           filter_role=filter_role, filter_status=filter_status)


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    from flask import render_template as rt
    user = User.query.get_or_404(user_id)
    was_active = user.is_active
    user.is_active   = request.form.get('is_active') == 'on'
    user.is_verified = request.form.get('is_verified') == 'on'
    db.session.commit()

    # Send approval / rejection email only when the status actually changes
    try:
        from flask_mail import Message as MailMsg
        from app import mail
        if not was_active and user.is_active:
            html = rt('email/account_approved.html',
                      username=user.username, role=user.role,
                      login_url=url_for('auth.login', _external=True))
            msg = MailMsg('Mode S7vn — Your Account Has Been Approved',
                          recipients=[user.email], html=html)
            mail.send(msg)
        elif was_active and not user.is_active:
            reason = request.form.get('rejection_reason', '').strip()
            html = rt('email/account_rejected.html',
                      username=user.username, reason=reason)
            msg = MailMsg('Mode S7vn — Account Status Update',
                          recipients=[user.email], html=html)
            mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Account status email failed: {e}')

    action = 'approved' if user.is_active else 'deactivated'
    flash(f'User {user.username} {action}.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/ban', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin():
        flash('Cannot ban an admin account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    reason = request.form.get('ban_reason', '').strip() or 'Violation of terms of service'
    user.is_banned  = True
    user.is_active  = False
    user.ban_reason = reason
    db.session.commit()
    flash(f'{user.username} has been banned.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/unban', methods=['POST'])
@login_required
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned  = False
    user.is_active  = True
    user.ban_reason = None
    db.session.commit()
    flash(f'{user.username} has been unbanned and reactivated.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin():
        flash('Cannot change role of an admin account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    new_role = request.form.get('new_role', '').strip()
    valid_roles = [UserRole.BUYER.value, UserRole.SELLER.value, UserRole.RIDER.value]
    if new_role not in valid_roles:
        flash('Invalid role.', 'danger')
        return redirect(url_for('admin.manage_users'))
    user.role = new_role
    db.session.commit()
    flash(f'{user.username} role changed to {new_role.upper()}.', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def admin_reset_password(user_id):
    import uuid
    from datetime import datetime, timedelta
    user = User.query.get_or_404(user_id)
    token  = uuid.uuid4().hex
    expiry = datetime.utcnow() + timedelta(hours=24)
    user.reset_token        = token
    user.reset_token_expiry = expiry
    db.session.commit()
    # Build reset link
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    # Try to send email
    try:
        from flask_mail import Message
        from app import mail
        from flask import render_template as rt
        msg = Message('Mode S7vn — Password Reset (Admin)',
                      recipients=[user.email],
                      html=rt('email/reset_password.html',
                              username=user.username, reset_url=reset_url))
        mail.send(msg)
        flash(f'Password reset email sent to {user.email}.', 'success')
    except Exception:
        flash(f'Reset link generated (email failed). Link: {reset_url}', 'warning')
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
    page          = request.args.get('page', 1, type=int)
    filter_status = request.args.get('status', '')
    search        = request.args.get('q', '').strip()

    query = Order.query
    if filter_status:
        query = query.filter_by(status=filter_status)
    if search:
        buyer_ids = [u.id for u in User.query.filter(User.username.ilike(f'%{search}%')).all()]
        query = query.filter(
            db.or_(Order.order_number.ilike(f'%{search}%'),
                   Order.buyer_id.in_(buyer_ids))
        )

    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20)
    riders = User.query.filter_by(role=UserRole.RIDER.value, is_active=True).all()
    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    )
    return render_template('admin/orders.html', orders=orders, riders=riders,
                           filter_status=filter_status, search=search,
                           status_counts=status_counts)


@admin_bp.route('/orders/<int:order_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    from datetime import datetime
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', '').strip()
    valid = [s.value for s in OrderStatus]
    if new_status not in valid:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin.manage_orders'))
    order.status = new_status
    if new_status == OrderStatus.DELIVERED.value:
        order.delivered_at = datetime.utcnow()
    db.session.commit()
    flash(f'Order {order.order_number} updated to {new_status.upper()}.', 'success')
    return redirect(url_for('admin.manage_orders', status=request.args.get('status', '')))

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
    revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(status=OrderStatus.DELIVERED.value).scalar() or 0

    status_counts = dict(
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status).all()
    )
    role_counts = dict(
        db.session.query(User.role, func.count(User.id))
        .group_by(User.role).all()
    )
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


@admin_bp.route('/reports/export-pdf')
@login_required
@admin_required
def export_reports_pdf():
    from datetime import datetime
    from io import BytesIO
    from flask import make_response
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    # ── Data ──────────────────────────────────────────────────────────────────
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    query = Order.query.order_by(Order.created_at.asc())
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to + ' 23:59:59')
    orders = query.all()

    revenue_total = sum(o.total_amount for o in orders if o.status == OrderStatus.DELIVERED.value)
    status_counts = {}
    for o in orders:
        status_counts[o.status] = status_counts.get(o.status, 0) + 1

    # ── PDF setup ─────────────────────────────────────────────────────────────
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm
    )

    W = A4[0] - 36*mm   # usable width
    styles = getSampleStyleSheet()
    BLACK  = colors.HexColor('#111827')
    GRAY   = colors.HexColor('#6b7280')
    LGRAY  = colors.HexColor('#f3f4f6')
    MGRAY  = colors.HexColor('#e5e7eb')
    WHITE  = colors.white

    h1 = ParagraphStyle('h1', fontSize=18, fontName='Helvetica-Bold',
                         textColor=BLACK, spaceAfter=2)
    h2 = ParagraphStyle('h2', fontSize=10, fontName='Helvetica-Bold',
                         textColor=BLACK, spaceBefore=14, spaceAfter=4)
    sub = ParagraphStyle('sub', fontSize=8, fontName='Helvetica',
                          textColor=GRAY, spaceAfter=0)
    small = ParagraphStyle('small', fontSize=7.5, fontName='Helvetica',
                            textColor=GRAY)
    cell_normal = ParagraphStyle('cn', fontSize=8, fontName='Helvetica',
                                  textColor=BLACK, leading=10)
    cell_bold   = ParagraphStyle('cb', fontSize=8, fontName='Helvetica-Bold',
                                  textColor=BLACK, leading=10)

    generated_at = datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')
    period_label = ''
    if date_from and date_to:
        period_label = f'Period: {date_from} to {date_to}'
    elif date_from:
        period_label = f'From: {date_from}'
    elif date_to:
        period_label = f'Up to: {date_to}'
    else:
        period_label = 'All time'

    story = []

    # ── Header block ─────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('MODE S7VN', ParagraphStyle('brand', fontSize=20,
            fontName='Helvetica-Bold', textColor=BLACK)),
        Paragraph(f'Generated: {generated_at}<br/>{period_label}',
                  ParagraphStyle('meta', fontSize=8, fontName='Helvetica',
                                  textColor=GRAY, alignment=TA_RIGHT))
    ]]
    header_tbl = Table(header_data, colWidths=[W*0.55, W*0.45])
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_tbl)
    story.append(Paragraph('Admin Platform Report', sub))
    story.append(HRFlowable(width=W, thickness=1, color=MGRAY, spaceAfter=10))

    # ── Summary KPIs ─────────────────────────────────────────────────────────
    story.append(Paragraph('Summary', h2))
    delivered = status_counts.get('delivered', 0)
    pending   = status_counts.get('pending', 0)
    cancelled = status_counts.get('cancelled', 0)

    kpi_data = [
        ['Total Orders', 'Delivered', 'Pending', 'Cancelled', 'Revenue (Delivered)'],
        [
            str(len(orders)),
            str(delivered),
            str(pending),
            str(cancelled),
            f'PHP {revenue_total:,.2f}'
        ]
    ]
    kpi_col = W / 5
    kpi_tbl = Table(kpi_data, colWidths=[kpi_col]*5)
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,0), LGRAY),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 8),
        ('FONTNAME',     (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,1), (-1,1), 11),
        ('TEXTCOLOR',    (0,0), (-1,0), GRAY),
        ('TEXTCOLOR',    (0,1), (-1,1), BLACK),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('BOX',          (0,0), (-1,-1), 0.5, MGRAY),
        ('INNERGRID',    (0,0), (-1,-1), 0.5, MGRAY),
        ('ROWBACKGROUNDS',(0,1),(-1,1), [WHITE]),
    ]))
    story.append(kpi_tbl)

    # ── Status breakdown ─────────────────────────────────────────────────────
    story.append(Paragraph('Order Status Breakdown', h2))
    all_statuses = ['pending','verified','assigned','shipped','delivered','cancelled']
    sb_data = [['Status', 'Count', 'Share']]
    total_o = len(orders) or 1
    for s in all_statuses:
        cnt = status_counts.get(s, 0)
        sb_data.append([s.upper(), str(cnt), f'{cnt/total_o*100:.1f}%'])

    sb_tbl = Table(sb_data, colWidths=[W*0.5, W*0.25, W*0.25])
    sb_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), LGRAY),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 8),
        ('TEXTCOLOR',     (0,0), (-1,0), GRAY),
        ('TEXTCOLOR',     (0,1), (-1,-1), BLACK),
        ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('BOX',           (0,0), (-1,-1), 0.5, MGRAY),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, MGRAY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, LGRAY]),
    ]))
    story.append(sb_tbl)

    # ── Order detail table ────────────────────────────────────────────────────
    story.append(Paragraph('Order Details', h2))

    col_widths = [W*0.18, W*0.12, W*0.12, W*0.16, W*0.14, W*0.14, W*0.14]
    tbl_data = [[
        Paragraph('Order ID', cell_bold),
        Paragraph('Date', cell_bold),
        Paragraph('Time (UTC)', cell_bold),
        Paragraph('Buyer', cell_bold),
        Paragraph('Buyer ID', cell_bold),
        Paragraph('Status', cell_bold),
        Paragraph('Total', cell_bold),
    ]]

    for o in orders:
        tbl_data.append([
            Paragraph(o.order_number, cell_normal),
            Paragraph(o.created_at.strftime('%Y-%m-%d'), cell_normal),
            Paragraph(o.created_at.strftime('%H:%M:%S'), cell_normal),
            Paragraph(o.buyer.username if o.buyer else '—', cell_normal),
            Paragraph(str(o.buyer_id), cell_normal),
            Paragraph(o.status.upper(), cell_normal),
            Paragraph(f'PHP {o.total_amount:,.2f}', cell_normal),
        ])

    if len(tbl_data) == 1:
        tbl_data.append([Paragraph('No orders found.', cell_normal)] + [''] * 6)

    order_tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)
    order_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), LGRAY),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('TEXTCOLOR',     (0,0), (-1,0), GRAY),
        ('TEXTCOLOR',     (0,1), (-1,-1), BLACK),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
        ('BOX',           (0,0), (-1,-1), 0.5, MGRAY),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, MGRAY),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, LGRAY]),
    ]))
    story.append(order_tbl)

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=MGRAY, spaceAfter=4))
    story.append(Paragraph(
        f'This report was generated automatically by Mode S7vn Admin Portal · {generated_at} · '
        f'Total records: {len(orders)}',
        small
    ))

    doc.build(story)
    buf.seek(0)

    filename = f"mode_s7vn_report_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.pdf"
    response = make_response(buf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
