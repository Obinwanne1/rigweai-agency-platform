import sqlite3
from collections import defaultdict
from flask import g
from config import Config

VALID_STATUSES = ("active", "assigned", "work_in_progress", "completed", "paused", "cancelled")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(Config.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
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


def bulk_project_members(conn: sqlite3.Connection, project_ids: list[int]) -> dict[int, list[dict]]:
    """Fetch members for multiple projects in one query. Returns {project_id: [members]}."""
    if not project_ids:
        return {}
    placeholders = ",".join("?" * len(project_ids))
    rows = conn.execute(
        f"""
        SELECT pm.project_id, u.id, u.name, u.email,
               u.role AS user_role, pm.role AS member_role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id IN ({placeholders})
        """,
        project_ids,
    ).fetchall()
    result = defaultdict(list)
    for r in rows:
        d = dict(r)
        pid = d.pop("project_id")
        result[pid].append(d)
    return result
