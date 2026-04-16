from . import db
from datetime import datetime
from enum import Enum

class PaymentStatus(Enum):
    PENDING = 'pending'
    COLLECTED = 'collected'  # Rider collected cash from buyer
    REFUNDED = 'refunded'

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(10), default='cod', nullable=False)
    status = db.Column(db.String(20), default=PaymentStatus.PENDING.value)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.id}>'
