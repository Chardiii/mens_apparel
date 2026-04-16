from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Product, Order, Message
from sqlalchemy import or_, and_

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')


def _conversation_partner_ids():
    """Return distinct user IDs the current user has exchanged messages with."""
    sent     = db.session.query(Message.receiver_id).filter_by(sender_id=current_user.id)
    received = db.session.query(Message.sender_id).filter_by(receiver_id=current_user.id)
    ids = {r[0] for r in sent.all()} | {r[0] for r in received.all()}
    return ids


@messages_bp.route('/')
@login_required
def inbox():
    partner_ids = _conversation_partner_ids()
    partners = User.query.filter(User.id.in_(partner_ids)).all() if partner_ids else []

    # Attach last message + unread count per partner
    conversations = []
    for p in partners:
        last = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id,   Message.receiver_id == p.id),
                and_(Message.sender_id == p.id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.created_at.desc()).first()

        unread = Message.query.filter_by(
            sender_id=p.id, receiver_id=current_user.id, is_read=False
        ).count()

        conversations.append({'partner': p, 'last': last, 'unread': unread})

    conversations.sort(key=lambda x: x['last'].created_at if x['last'] else 0, reverse=True)
    total_unread = sum(c['unread'] for c in conversations)
    return render_template('messages/inbox.html',
                           conversations=conversations,
                           total_unread=total_unread)


@messages_bp.route('/thread/<int:partner_id>', methods=['GET', 'POST'])
@login_required
def thread(partner_id):
    partner = User.query.get_or_404(partner_id)
    product_id = request.args.get('product_id', type=int)
    order_id   = request.args.get('order_id',   type=int)

    if request.method == 'POST':
        body = request.form.get('body', '').strip()
        if not body:
            flash('Message cannot be empty.', 'warning')
            return redirect(url_for('messages.thread', partner_id=partner_id,
                                    product_id=product_id, order_id=order_id))
        if len(body) > 2000:
            flash('Message too long (max 2000 characters).', 'warning')
            return redirect(url_for('messages.thread', partner_id=partner_id))

        msg = Message(
            sender_id=current_user.id,
            receiver_id=partner_id,
            product_id=product_id,
            order_id=order_id,
            body=body
        )
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('messages.thread', partner_id=partner_id,
                                product_id=product_id, order_id=order_id) + '#bottom')

    # Mark all incoming messages from this partner as read
    Message.query.filter_by(
        sender_id=partner_id, receiver_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()

    msgs = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id,   Message.receiver_id == partner_id),
            and_(Message.sender_id == partner_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()

    context_product = Product.query.get(product_id) if product_id else None
    context_order   = Order.query.get(order_id)     if order_id   else None

    return render_template('messages/thread.html',
                           partner=partner,
                           msgs=msgs,
                           context_product=context_product,
                           context_order=context_order,
                           product_id=product_id,
                           order_id=order_id)


@messages_bp.route('/unread-count')
@login_required
def unread_count():
    count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})
