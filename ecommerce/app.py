from flask import Flask
from flask_login import LoginManager
from config import config
from models import db, User
from routes import auth_bp, main_bp, products_bp, orders_bp, admin_bp, wishlist_bp
import os

def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(wishlist_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return 'Page not found', 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return 'An internal error occurred', 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
