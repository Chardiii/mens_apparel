from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Product, ProductImage, Order, OrderItem, Review
from sqlalchemy import func
import os
import uuid

products_bp = Blueprint('products', __name__, url_prefix='/products')

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

    # All distinct categories for sidebar
    categories = [r[0] for r in
        db.session.query(Product.category)
        .filter(Product.is_active == True, Product.category != None, Product.category != '')
        .distinct().order_by(Product.category).all()
    ]

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

    products = Product.query.filter_by(seller_id=current_user.id).all()

    total_orders = db.session.query(func.count(Order.id))\
        .filter_by(seller_id=current_user.id).scalar() or 0
    pending_orders = db.session.query(func.count(Order.id))\
        .filter_by(seller_id=current_user.id, status='pending').scalar() or 0
    revenue = db.session.query(func.sum(Order.total_amount))\
        .filter_by(seller_id=current_user.id, status='delivered').scalar() or 0

    stats = {
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'revenue': round(float(revenue), 2)
    }

    return render_template('seller_dashboard.html', products=products, stats=stats)


@products_bp.route('/seller/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_seller():
        flash('Only sellers can add products.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        stock = request.form.get('stock', type=int)
        category = request.form.get('category')

        if not all([name, price, stock]):
            flash('Name, price, and stock are required.', 'danger')
            return redirect(url_for('products.add_product'))

        product = Product(seller_id=current_user.id, name=name,
                          description=description, price=price,
                          stock=stock, category=category)
        db.session.add(product)
        db.session.flush()

        # Handle image uploads
        images = request.files.getlist('images')
        first = True
        for file in images:
            if file and file.filename and allowed_file(file.filename):
                filename = save_image(file)
                db.session.add(ProductImage(
                    product_id=product.id,
                    image_url=filename,
                    is_primary=first
                ))
                first = False

        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products.seller_dashboard'))

    return render_template('add_product.html')


@products_bp.route('/seller/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.seller_id != current_user.id and not current_user.is_admin():
        flash('Not authorized.', 'danger')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        product.name = request.form.get('name', product.name)
        product.description = request.form.get('description', product.description)
        product.price = request.form.get('price', type=float) or product.price
        product.stock = request.form.get('stock', type=int) or product.stock
        product.category = request.form.get('category', product.category)

        # New images
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

    return render_template('edit_product.html', product=product)


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
