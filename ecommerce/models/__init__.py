from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

from .user import User, UserRole
from .product import Product, ProductImage
from .order import Order, OrderItem, OrderStatus
from .payment import Payment, PaymentStatus
from .review import Review
from .wishlist import Wishlist

__all__ = ['db', 'User', 'UserRole', 'Product', 'ProductImage', 'Order', 'OrderItem',
           'OrderStatus', 'Payment', 'PaymentStatus', 'Review', 'Wishlist']
