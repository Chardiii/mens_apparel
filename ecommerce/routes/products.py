from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Product, ProductImage, ProductVariant, Order, OrderItem, Review
from sqlalchemy import func
import os
import uuid

products_bp = Blueprint('products', __name__, url_prefix='/products')

CATEGORIES = [
    'Suits & Blazers',
    'Casual Shirts & Pants',
    'Outerwear & Jackets',
    'Activewear & Fitness Gear',
    'Shoes & Accessories',
    'Grooming Products',
]

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))
    return filename


# ── Public routes ─────────────────────────────────────────────────────────────

@products_bp.route('/')
def list_products():
    page      = request.args.get('page', 1, type=int)
    search    = request.args.get('search', '').strip()
    category  = request.args.get('category', '')
    sort      = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '', type=str).strip()
    max_price = request.args.get('max_price', '', type=str).strip()
    in_stock  = request.args.get('in_stock', '') == '1'

    query = Product.query.filter_by(is_active=True)

    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)
    if min_price:
        query = query.filter(Product.price >= float(min_price))
    if max_price:
        query = query.filter(Product.price <= float(max_price))
    if in_stock:
        query = query.filter(Product.stock > 0)

    sort_map = {
        'newest':    Product.created_at.desc(),
        'oldest':    Product.created_at.asc(),
        'price_asc': Product.price.asc(),
        'price_desc':Product.price.desc(),
        'rating':    Product.rating.desc(),
        'name':      Product.name.asc(),
    }
    query = query.order_by(sort_map.get(sort, Product.created_at.desc()))

    products = query.paginate(page=page, per_page=12)

    # Fixed category list
    categories = CATEGORIES

    filters = dict(search=search, category=category, sort=sort,
                   min_price=min_price, max_price=max_price,
                   in_stock='1' if in_stock else '')

    return render_template('products.html', products=products,
                           categories=categories, filters=filters)


@products_bp.route('/search-suggestions')
def search_suggestions():
    from flask import jsonify
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Product.query.filter(
        Product.is_active == True,
        Product.name.ilike(f'%{q}%')
    ).limit(6).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': p.price,
                     'category': p.category or ''} for p in results])


@products_bp.route('/<int:product_id>')
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = product.reviews.order_by(Review.created_at.desc()).all()

    user_has_reviewed = False
    user_has_purchased = False
    wishlist_status = False
    if current_user.is_authenticated and current_user.is_buyer():
        from models import Wishlist
        user_has_reviewed = Review.query.filter_by(
            product_id=product_id, reviewer_id=current_user.id
        ).first() is not None
        user_has_purchased = db.session.query(OrderItem).join(Order).filter(
            OrderItem.product_id == product_id,
            Order.buyer_id == current_user.id,
            Order.status == 'delivered'
        ).first() is not None
        wishlist_status = Wishlist.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first() is not None

    return render_template('product_detail.html',
                           product=product,
                           reviews=reviews,
                           user_has_reviewed=user_has_reviewed,
                           user_has_purchased=user_has_purchased,
                           wishlist_status=wishlist_status)


# ── Review ────────────────────────────────────────────────────────────────────

@products_bp.route('/<int:product_id>/review', methods=['POST'])
@login_required
def submit_review(product_id):
    product = Product.query.get_or_404(product_id)

    if not current_user.is_buyer():
        flash('Only buyers can leave reviews.', 'danger')
        return redirect(url_for('products.view_product', product_id=product_id))

    if Review.query.filter_by(product_id=product_id, reviewer_id=current_user.id).first():
        flash('You have already reviewed this product.', 'warning')
        return redirect(url_for('products.view_product', product_id=product_id))

    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or not (1 <= rating <= 5):
        flash('Please select a rating between 1 and 5.', 'danger')
        return redirect(url_for('products.view_product', product_id=product_id))

    review = Review(product_id=product_id, reviewer_id=current_user.id,
                    rating=rating, comment=comment)
    db.session.add(review)

    # Recalculate product rating
    db.session.flush()
    avg = db.session.query(func.avg(Review.rating)).filter_by(product_id=product_id).scalar()
    count = Review.query.filter_by(product_id=product_id).count()
    product.rating = round(float(avg), 1)
    product.review_count = count

    db.session.commit()
    flash('Review submitted!', 'success')
    return redirect(url_for('products.view_product', product_id=product_id))


# ── Seller routes ─────────────────────────────────────────────────────────────

@products_bp.route('/seller/dashboard')
@login_required
def seller_dashboard():
    if not current_user.is_seller():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))

    from datetime import date, timedelta

    # Inventory filters
    inv_search       = request.args.get('q', '').strip()
    inv_stock_filter = request.args.get('stock_filter', '')
    inv_cat_filter   = request.args.get('cat_filter', '')

    pq = Product.query.filter_by(seller_id=current_user.id)
    if inv_search:
        pq = pq.filter(Product.name.ilike(f'%{inv_search}%'))
    if inv_stock_filter == 'out':
        pq = pq.filter(Product.stock == 0)
    elif inv_stock_filter == 'low':
        pq = pq.filter(Product.stock > 0, Product.stock <= 5)
    elif inv_stock_filter == 'in':
        pq = pq.filter(Product.stock > 0)
    if inv_cat_filter:
        pq = pq.filter_by(category=inv_cat_filter)
    products = pq.order_by(Product.created_at.desc()).all()

    # Core order stats
    total_orders     = Order.query.filter_by(seller_id=current_user.id).count()
    pending_orders   = Order.query.filter_by(seller_id=current_user.id, status='pending').count()
    delivered_orders = Order.query.filter_by(seller_id=current_user.id, status='delivered').count()
    revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(seller_id=current_user.id, status='delivered').scalar() or 0

    # Revenue trend vs previous 7 days
    today = date.today()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    rev_this_week = db.session.query(func.sum(Order.total_amount)).filter(
        Order.seller_id == current_user.id,
        Order.status == 'delivered',
        func.date(Order.delivered_at) >= week_ago
    ).scalar() or 0
    rev_last_week = db.session.query(func.sum(Order.total_amount)).filter(
        Order.seller_id == current_user.id,
        Order.status == 'delivered',
        func.date(Order.delivered_at) >= two_weeks_ago,
        func.date(Order.delivered_at) < week_ago
    ).scalar() or 0
    if rev_last_week:
        revenue_trend = round((float(rev_this_week) - float(rev_last_week)) / float(rev_last_week) * 100, 1)
    elif rev_this_week:
        revenue_trend = 100.0
    else:
        revenue_trend = 0.0

    # Product stats
    all_products     = Product.query.filter_by(seller_id=current_user.id).all()
    total_products   = len(all_products)
    active_products  = sum(1 for p in all_products if p.is_active)
    out_of_stock     = sum(1 for p in all_products if p.stock == 0)
    low_stock_list   = [p for p in all_products if 0 < p.stock <= 5]
    low_stock_count  = len(low_stock_list)

    # Ratings
    ratings = [p.rating for p in all_products if p.review_count > 0]
    avg_rating   = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
    total_reviews = sum(p.review_count for p in all_products)

    # 7-day revenue chart
    chart_labels, chart_revenue = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_rev = db.session.query(func.sum(Order.total_amount)).filter(
            Order.seller_id == current_user.id,
            Order.status == 'delivered',
            func.date(Order.delivered_at) == day
        ).scalar() or 0
        chart_labels.append(day.strftime('%b %d'))
        chart_revenue.append(round(float(day_rev), 2))

    # Orders by status for donut
    status_rows = db.session.query(Order.status, func.count(Order.id))\
        .filter_by(seller_id=current_user.id).group_by(Order.status).all()
    status_labels = [r[0] for r in status_rows]
    status_data   = [r[1] for r in status_rows]

    recent_orders = Order.query.filter_by(seller_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(5).all()

    stats = {
        'revenue':          round(float(revenue), 2),
        'revenue_trend':    revenue_trend,
        'total_orders':     total_orders,
        'pending_orders':   pending_orders,
        'delivered_orders': delivered_orders,
        'total_products':   total_products,
        'active_products':  active_products,
        'out_of_stock':     out_of_stock,
        'low_stock_products': low_stock_count,
        'low_stock_list':   low_stock_list,
        'avg_rating':       avg_rating,
        'total_reviews':    total_reviews,
    }

    return render_template('seller_dashboard.html',
                           products=products, stats=stats,
                           recent_orders=recent_orders,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           status_labels=status_labels,
                           status_data=status_data,
                           categories=CATEGORIES,
                           inv_search=inv_search,
                           inv_stock_filter=inv_stock_filter,
                           inv_cat_filter=inv_cat_filter)


@products_bp.route('/seller/orders')
@login_required
def seller_orders():
    if not current_user.is_seller():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))
    filter_status = request.args.get('status', '')
    query = Order.query.filter_by(seller_id=current_user.id)
    if filter_status:
        query = query.filter_by(status=filter_status)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template('seller_orders.html', orders=orders, filter_status=filter_status)


@products_bp.route('/seller/products/<int:product_id>/toggle', methods=['POST'])
@login_required
def seller_toggle_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != current_user.id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('products.seller_dashboard'))
    product.is_active = not product.is_active
    db.session.commit()
    return redirect(url_for('products.seller_dashboard') + '#inventory')


@products_bp.route('/seller/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_seller():
        flash('Only sellers can add products.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name        = request.form.get('name')
        description = request.form.get('description')
        price       = request.form.get('price', type=float)
        category    = request.form.get('category')

        if not all([name, price, category]):
            flash('Name, price, and category are required.', 'danger')
            return redirect(url_for('products.add_product'))

        # Variant data
        v_sizes     = request.form.getlist('variant_size[]')
        v_colors    = request.form.getlist('variant_color[]')
        v_stocks    = request.form.getlist('variant_stock[]')
        v_price_adj = request.form.getlist('variant_price_adj[]')
        has_variants = any(s.strip() for s in v_sizes)

        if has_variants:
            total_stock = sum(int(s or 0) for s in v_stocks)
        else:
            total_stock = request.form.get('stock', 0, type=int)

        product = Product(
            seller_id=current_user.id, name=name,
            description=description, price=price,
            stock=total_stock, category=category
        )
        db.session.add(product)
        db.session.flush()

        # Save variants
        if has_variants:
            for i, size in enumerate(v_sizes):
                if not size.strip():
                    continue
                db.session.add(ProductVariant(
                    product_id=product.id,
                    size=size.strip(),
                    color=(v_colors[i].strip() if i < len(v_colors) else '') or None,
                    stock=int(v_stocks[i]) if i < len(v_stocks) and v_stocks[i] else 0,
                    price_adj=float(v_price_adj[i]) if i < len(v_price_adj) and v_price_adj[i] else 0.0,
                    sku=f"{product.id}-{size.strip()}-{(v_colors[i].strip() if i < len(v_colors) else '') or 'NA'}"
                ))

        # Images
        images = request.files.getlist('images')
        first = True
        for file in images:
            if file and file.filename and allowed_file(file.filename):
                filename = save_image(file)
                db.session.add(ProductImage(
                    product_id=product.id, image_url=filename, is_primary=first
                ))
                first = False

        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products.seller_dashboard'))

    return render_template('add_product.html', categories=CATEGORIES)


@products_bp.route('/seller/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.seller_id != current_user.id and not current_user.is_admin():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        product.name        = request.form.get('name', product.name).strip()
        product.description = request.form.get('description', product.description)
        new_price           = request.form.get('price', type=float)
        if new_price is not None:
            product.price   = new_price
        product.category    = request.form.get('category', product.category)

        # ── Variant handling ──────────────────────────────────────────────
        v_ids       = request.form.getlist('variant_id[]')
        v_sizes     = request.form.getlist('variant_size[]')
        v_colors    = request.form.getlist('variant_color[]')
        v_stocks    = request.form.getlist('variant_stock[]')
        v_price_adj = request.form.getlist('variant_price_adj[]')

        has_variants = any(s.strip() for s in v_sizes)

        if has_variants:
            submitted_ids = set()
            for i, size in enumerate(v_sizes):
                if not size.strip():
                    continue
                vid       = int(v_ids[i]) if i < len(v_ids) and v_ids[i] else None
                color     = (v_colors[i].strip() if i < len(v_colors) else '') or None
                stock     = int(v_stocks[i]) if i < len(v_stocks) and v_stocks[i] else 0
                price_adj = float(v_price_adj[i]) if i < len(v_price_adj) and v_price_adj[i] else 0.0

                if vid:
                    variant = ProductVariant.query.get(vid)
                    if variant and variant.product_id == product.id:
                        variant.size      = size.strip()
                        variant.color     = color
                        variant.stock     = stock
                        variant.price_adj = price_adj
                        submitted_ids.add(vid)
                else:
                    new_v = ProductVariant(
                        product_id=product.id,
                        size=size.strip(),
                        color=color,
                        stock=stock,
                        price_adj=price_adj,
                        sku=f"{product.id}-{size.strip()}-{color or 'NA'}"
                    )
                    db.session.add(new_v)
                    db.session.flush()
                    submitted_ids.add(new_v.id)

            for existing in product.variants.all():
                if existing.id not in submitted_ids:
                    db.session.delete(existing)

            db.session.flush()
            product.stock = sum(v.stock for v in product.variants.all())
        else:
            flat_stock = request.form.get('stock', type=int)
            if flat_stock is not None:
                product.stock = flat_stock
            for v in product.variants.all():
                db.session.delete(v)
        # ── Images ───────────────────────────────────────────────────────
        images = request.files.getlist('images')
        has_primary = product.images.filter_by(is_primary=True).first() is not None
        for file in images:
            if file and file.filename and allowed_file(file.filename):
                filename = save_image(file)
                db.session.add(ProductImage(
                    product_id=product.id,
                    image_url=filename,
                    is_primary=not has_primary
                ))
                has_primary = True

        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products.seller_dashboard'))

    # Build size options for the template based on current category
    size_map = {
        'Suits & Blazers':           ['XS','S','M','L','XL','XXL'],
        'Casual Shirts & Pants':     ['XS','S','M','L','XL','XXL'],
        'Outerwear & Jackets':       ['XS','S','M','L','XL','XXL'],
        'Activewear & Fitness Gear': ['XS','S','M','L','XL','XXL'],
        'Shoes & Accessories':       ['38','39','40','41','42','43','44','45'],
    }
    size_options = size_map.get(product.category, [])

    return render_template('edit_product.html', product=product,
                           categories=CATEGORIES, size_options=size_options)


@products_bp.route('/seller/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.seller_id != current_user.id and not current_user.is_admin():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))

    # Delete image files from disk
    for img in product.images:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.image_url)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('products.seller_dashboard'))


@products_bp.route('/image/delete/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    image = ProductImage.query.get_or_404(image_id)
    product = image.product

    if product.seller_id != current_user.id and not current_user.is_admin():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))

    path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_url)
    if os.path.exists(path):
        os.remove(path)

    # If deleted image was primary, promote next image
    was_primary = image.is_primary
    db.session.delete(image)
    db.session.flush()

    if was_primary:
        next_img = ProductImage.query.filter_by(product_id=product.id).first()
        if next_img:
            next_img.is_primary = True

    db.session.commit()
    flash('Image deleted.', 'info')
    return redirect(url_for('products.edit_product', product_id=product.id))
