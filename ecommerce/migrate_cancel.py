"""
Add cancel tracking columns to orders table
"""
from app import create_app
from models import db

app = create_app()

with app.app_context():
    # Add the new columns using raw SQL
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("""
                ALTER TABLE orders 
                ADD COLUMN cancel_reason VARCHAR(500),
                ADD COLUMN cancel_requested_by VARCHAR(10),
                ADD COLUMN cancel_status VARCHAR(10)
            """))
            conn.commit()
            print("[OK] Added cancel tracking columns to orders table")
        except Exception as e:
            if 'Duplicate column name' in str(e):
                print("[OK] Columns already exist")
            else:
                print(f"[ERROR] {e}")
