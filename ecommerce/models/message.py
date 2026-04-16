from . import db
from datetime import datetime


class Message(db.Model):
    __tablename__ = 'messages'

    id          = db.Column(db.Integer, primary_key=True)
    sender_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id  = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'),   nullable=True)
    body        = db.Column(db.Text, nullable=False)
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender   = db.relationship('User', foreign_keys=[sender_id],   backref=db.backref('sent_messages',     lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))

    def __repr__(self):
        return f'<Message {self.id} {self.sender_id}->{self.receiver_id}>'
