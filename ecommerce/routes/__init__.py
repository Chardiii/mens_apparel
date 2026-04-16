from .auth import auth_bp
from .main import main_bp
from .products import products_bp
from .orders import orders_bp
from .admin import admin_bp
from .wishlist import wishlist_bp
from .messages import messages_bp

__all__ = ['auth_bp', 'main_bp', 'products_bp', 'orders_bp', 'admin_bp', 'wishlist_bp', 'messages_bp']
