"""
Security migration — adds must_change_password, failed_attempts, locked_until
to users table and creates password_reset_tokens table.
Safe to run multiple times.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "agency.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        for col_sql in [
            "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN locked_until TEXT",
        ]:
            try:
                conn.execute(col_sql)
                col = col_sql.split("ADD COLUMN")[1].strip().split()[0]
                print(f"  + users.{col}")
            except Exception:
                col = col_sql.split("ADD COLUMN")[1].strip().split()[0]
                print(f"  ~ users.{col} already exists, skipped")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + password_reset_tokens table")
        conn.commit()
        print("Migration complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
