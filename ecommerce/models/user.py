from . import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum

class UserRole(Enum):
    """User roles in the system"""
    BUYER = 'buyer'
    SELLER = 'seller'
    ADMIN = 'admin'
    RIDER = 'rider'

class User(UserMixin, db.Model):
    """User model for all roles"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default=UserRole.BUYER.value, nullable=False)
    
    # Seller specific fields
    shop_name = db.Column(db.String(120))
    shop_description = db.Column(db.Text)
    shop_rating = db.Column(db.Float, default=0.0)
    
    # Rider specific fields
    vehicle_type = db.Column(db.String(50))
    vehicle_number = db.Column(db.String(50))

    # Verification documents
    valid_id = db.Column(db.String(255))           # all roles
    business_permit = db.Column(db.String(255))    # seller only
    drivers_license = db.Column(db.String(255))    # rider only
    plate_number = db.Column(db.String(50))        # rider only
    
    # Profile
    profile_picture = db.Column(db.String(255))
    street       = db.Column(db.String(255))   # house/unit/street
    barangay     = db.Column(db.String(120))
    municipality = db.Column(db.String(120))
    province     = db.Column(db.String(120))
    region       = db.Column(db.String(120))
    address      = db.Column(db.Text)          # legacy / full address fallback
    city         = db.Column(db.String(80))    # legacy
    zip_code     = db.Column(db.String(10))
    
    # Account status
    is_active = db.Column(db.Boolean, default=False, nullable=False)  # requires admin approval
    is_verified = db.Column(db.Boolean, default=False)  # admin approval flag
    is_banned = db.Column(db.Boolean, default=False)    # permanently banned
    ban_reason = db.Column(db.String(255))
    email_verified = db.Column(db.Boolean, default=False)  # email verification flag
    email_verify_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='seller', lazy='dynamic', foreign_keys='Product.seller_id')
    orders = db.relationship('Order', backref='buyer', lazy='dynamic', foreign_keys='Order.buyer_id')
    seller_orders = db.relationship('Order', backref='seller_user', lazy='dynamic', foreign_keys='Order.seller_id')
    deliveries = db.relationship('Order', backref='rider', lazy='dynamic', foreign_keys='Order.rider_id')
    reviews = db.relationship('Review', backref='reviewer', lazy='dynamic', foreign_keys='Review.reviewer_id')
    wishlists = db.relationship('Wishlist', backref='user', lazy='dynamic', foreign_keys='Wishlist.user_id')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_seller(self):
        """Check if user is a seller"""
        return self.role == UserRole.SELLER.value
    
    def is_buyer(self):
        """Check if user is a buyer"""
        return self.role == UserRole.BUYER.value
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == UserRole.ADMIN.value
    
    def is_rider(self):
        return self.role == UserRole.RIDER.value

    @property
    def full_address(self):
        parts = [p for p in [self.street, self.barangay, self.municipality,
                              self.province, self.region] if p]
        return ', '.join(parts) if parts else (self.address or '')

    def __repr__(self):
        return f'<User {self.username}>'
