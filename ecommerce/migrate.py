"""
Migration script — run once to update existing database schema.
Adds: orders.seller_id column
"""

from app import create_app
from models import db

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            # Check if seller_id already exists
            result = conn.execute(db.text(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'orders' "
                "AND COLUMN_NAME = 'seller_id'"
            ))
            exists = result.scalar()

            if exists:
                print("[OK] seller_id column already exists, nothing to do.")
            else:
                conn.execute(db.text(
                    "ALTER TABLE orders "
                    "ADD COLUMN seller_id INT NULL, "
                    "ADD INDEX ix_orders_seller_id (seller_id), "
                    "ADD CONSTRAINT fk_orders_seller_id "
                    "FOREIGN KEY (seller_id) REFERENCES users(id)"
                ))
                conn.commit()
                print("[OK] seller_id column added to orders table.")

        print("Migration complete.")

if __name__ == '__main__':
    migrate()
