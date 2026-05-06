import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import Config
from services.auth_service import hash_password

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # Seed default admin if none exists
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
            ("admin@rigweai.com", hash_password("admin123"), "Admin", "admin"),
        )
        conn.commit()
        print("Default admin created: admin@rigweai.com / admin123")
        print("IMPORTANT: Change the admin password after first login.")

    conn.close()
    print(f"Database initialized at {Config.DB_PATH}")


if __name__ == "__main__":
    init_db()
