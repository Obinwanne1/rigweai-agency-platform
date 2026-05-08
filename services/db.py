import sqlite3
from flask import g
from config import Config

VALID_STATUSES = ("active", "assigned", "work_in_progress", "completed", "paused", "cancelled")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(e=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def project_members(conn: sqlite3.Connection, project_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role AS user_role, pm.role AS member_role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id = ?
        """,
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]
