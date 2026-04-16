"""
Migration: add is_banned and ban_reason columns to users table.
Run once: python migrate_ban.py
"""
from app import create_app
from models import db

def migrate():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            cols = {
                'is_banned':  'TINYINT(1) NOT NULL DEFAULT 0',
                'ban_reason': 'VARCHAR(255) NULL',
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
