from . import db
from datetime import datetime
from enum import Enum

class OrderStatus(Enum):
    PENDING = 'pending'           # Buyer placed order
    VERIFIED = 'verified'         # Seller verified & ready to hand off
    ASSIGNED = 'assigned'         # Rider assigned
    SHIPPED = 'shipped'           # Rider picked up
    DELIVERED = 'delivered'       # Delivered to buyer
    CANCELLED = 'cancelled'
    CANCEL_REQUESTED = 'cancel_requested'  # Buyer requested cancel, awaiting seller

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default=OrderStatus.PENDING.value)
    
    delivery_address = db.Column(db.Text)
    delivery_city = db.Column(db.String(80))
    delivery_zip = db.Column(db.String(10))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    # Cancellation tracking
    cancel_reason       = db.Column(db.String(500))
    cancel_requested_by = db.Column(db.String(10))   # 'buyer' or 'seller'
    cancel_status       = db.Column(db.String(10))   # 'pending', 'approved', 'rejected'
    
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    quantity   = db.Column(db.Integer, nullable=False)
    price      = db.Column(db.Float, nullable=False)
    subtotal   = db.Column(db.Float, nullable=False)
    # snapshot of variant info at time of order
    variant_size  = db.Column(db.String(30), nullable=True)
    variant_color = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f'<OrderItem {self.id}>'
