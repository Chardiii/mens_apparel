"""
Database initialization script
Run this after starting the application to create test data
"""

from app import create_app, db
from models import User, Product, Order, Payment, UserRole

def init_db():
    """Initialize database with test data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created!")
        
        # Check if test users already exist
        if User.query.filter_by(username='admin').first():
            print("✓ Test data already exists!")
            return
        
        print("\nCreating test users...")
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@ecommerce.com',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN.value,
            is_active=True,
            is_verified=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create test seller
        seller = User(
            username='seller1',
            email='seller1@ecommerce.com',
            first_name='John',
            last_name='Seller',
            role=UserRole.SELLER.value,
            shop_name='John\'s Shop',
            shop_description='Amazing products at great prices!',
            is_active=True,
            is_verified=True
        )
        seller.set_password('seller123')
        db.session.add(seller)
        
        # Create test buyer
        buyer = User(
            username='buyer1',
            email='buyer1@ecommerce.com',
            first_name='Jane',
            last_name='Buyer',
            role=UserRole.BUYER.value,
            is_active=True,
            is_verified=True
        )
        buyer.set_password('buyer123')
        db.session.add(buyer)
        
        # Create test rider
        rider = User(
            username='rider1',
            email='rider1@ecommerce.com',
            first_name='Mike',
            last_name='Rider',
            role=UserRole.RIDER.value,
            vehicle_type='Bike',
            vehicle_number='AB-1234',
            is_active=True,
            is_verified=True
        )
        rider.set_password('rider123')
        db.session.add(rider)
        
        db.session.commit()
        print("✓ Test users created!")
        
        print("\nCreating test products...")
        
        # Create test products
        products = [
            {
                'name': 'Laptop',
                'description': 'High-performance laptop for work and gaming',
                'price': 999.99,
                'stock': 5,
                'category': 'Electronics'
            },
            {
                'name': 'Wireless Mouse',
                'description': 'Ergonomic wireless mouse with long battery life',
                'price': 29.99,
                'stock': 50,
                'category': 'Accessories'
            },
            {
                'name': 'USB-C Cable',
                'description': 'Fast charging USB-C cable 6ft',
                'price': 12.99,
                'stock': 100,
                'category': 'Accessories'
            },
            {
                'name': 'Mechanical Keyboard',
                'description': 'Professional mechanical keyboard with RGB lights',
                'price': 149.99,
                'stock': 20,
                'category': 'Accessories'
            },
            {
                'name': 'Monitor 4K',
                'description': '27-inch 4K UHD monitor',
                'price': 449.99,
                'stock': 10,
                'category': 'Electronics'
            }
        ]
        
        for prod_data in products:
            product = Product(
                seller_id=seller.id,
                **prod_data
            )
            db.session.add(product)
        
        db.session.commit()
        print("✓ Test products created!")
        
        print("\n" + "="*50)
        print("✓ Database initialized successfully!")
        print("="*50)
        print("\nTest Accounts Created:")
        print("  Admin    - username: admin, password: admin123")
        print("  Seller   - username: seller1, password: seller123")
        print("  Buyer    - username: buyer1, password: buyer123")
        print("  Rider    - username: rider1, password: rider123")
        print("\nTest Products: 5 sample products added")
        print("\nYou can now login at http://localhost:5000")

if __name__ == '__main__':
    init_db()
