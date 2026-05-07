"""
Migration v2: project_members + expanded status values.
Safe to run multiple times (idempotent).
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import Config


def run():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    # 1. Create project_members if missing
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('client', 'staff')),
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(project_id, user_id)
        )
    """)

    # 2. Check if projects still has staff_id column
    cols = [r[1] for r in conn.execute("PRAGMA table_info(projects)").fetchall()]
    has_staff_id = "staff_id" in cols

    if has_staff_id:
        # Migrate existing client_id → member role 'client'
        conn.execute("""
            INSERT OR IGNORE INTO project_members (project_id, user_id, role)
            SELECT id, client_id, 'client' FROM projects WHERE client_id IS NOT NULL
        """)
        # Migrate existing staff_id → member role 'staff'
        conn.execute("""
            INSERT OR IGNORE INTO project_members (project_id, user_id, role)
            SELECT id, staff_id, 'staff' FROM projects WHERE staff_id IS NOT NULL
        """)

        # Recreate projects without staff_id and with new status check
        conn.execute("""
            CREATE TABLE projects_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK(status IN ('active','assigned','work_in_progress','completed','paused','cancelled')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO projects_new (id, client_id, title, description, status, created_at)
            SELECT id, client_id, title, description, status, created_at FROM projects
        """)
        conn.execute("DROP TABLE projects")
        conn.execute("ALTER TABLE projects_new RENAME TO projects")
        print("Migrated projects table: removed staff_id, expanded status values.")
    else:
        # Already migrated — just ensure status constraint is current (no-op on SQLite)
        print("projects table already up to date.")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print("Migration v2 complete.")


if __name__ == "__main__":
    run()
