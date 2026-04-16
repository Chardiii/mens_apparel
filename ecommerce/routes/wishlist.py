from flask import Blueprint, render_template, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Wishlist, Product
from sqlalchemy.exc import IntegrityError

wishlist_bp = Blueprint('wishlist', __name__, url_prefix='/wishlist')


@wishlist_bp.route('/toggle/<int:product_id>', methods=['POST'])
@login_required
def toggle(product_id):
    """Add or remove from wishlist — returns JSON for AJAX."""
    if not current_user.is_buyer():
        return jsonify({'error': 'Only buyers can use the wishlist.'}), 403

    product = Product.query.get_or_404(product_id)
    existing = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'removed', 'message': f'{product.name} removed from wishlist.'})

    try:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        db.session.commit()
        return jsonify({'status': 'added', 'message': f'{product.name} added to wishlist!'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status': 'added', 'message': 'Already in wishlist.'})


@wishlist_bp.route('/')
@login_required
def view():
    if not current_user.is_buyer():
        flash('Only buyers have a wishlist.', 'warning')
        return redirect(url_for('main.index'))

    items = Wishlist.query.filter_by(user_id=current_user.id)\
        .order_by(Wishlist.created_at.desc()).all()
    return render_template('wishlist.html', items=items)


@wishlist_bp.route('/remove/<int:product_id>', methods=['POST'])
@login_required
def remove(product_id):
    item = Wishlist.query.filter_by(
        user_id=current_user.id, product_id=product_id
    ).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Removed from wishlist.', 'info')
    return redirect(url_for('wishlist.view'))
