"""
Migration: add email verification and password reset token columns to users.
Run once: python migrate_tokens.py
"""
from app import create_app
from models import db

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            cols = {
                'email_verified':      'TINYINT(1) NOT NULL DEFAULT 0',
                'email_verify_token':  'VARCHAR(100) NULL',
                'reset_token':         'VARCHAR(100) NULL',
                'reset_token_expiry':  'DATETIME NULL',
            }
            for col, definition in cols.items():
                exists = conn.execute(db.text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='users' "
                    f"AND COLUMN_NAME='{col}'"
                )).scalar()
                if not exists:
                    conn.execute(db.text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))
                    conn.commit()
                    print(f"[OK] Added: {col}")
                else:
                    print(f"[SKIP] Exists: {col}")
        print("Migration complete.")

if __name__ == '__main__':
    migrate()
