import sqlite3
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from config import Config

client_bp = Blueprint("client", __name__, url_prefix="/api/client")

VALID_STATUSES = ("active", "assigned", "work_in_progress", "completed", "paused", "cancelled")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _project_members(conn, project_id):
    rows = conn.execute("""
        SELECT u.id, u.name, u.email, u.role as user_role, pm.role as member_role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id = ?
    """, (project_id,)).fetchall()
    return [dict(r) for r in rows]


@client_bp.get("/projects")
@require_role("client", "admin", "staff")
def my_projects():
    conn = db()
    uid = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    try:
        rows = conn.execute("""
            SELECT DISTINCT p.*
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.id
            WHERE pm.user_id = ? AND pm.role = 'client'
            ORDER BY p.created_at DESC
        """, (uid,)).fetchall()
        projects = []
        for r in rows:
            p = dict(r)
            p["members"] = _project_members(conn, p["id"])
            projects.append(p)
    finally:
        conn.close()
    return jsonify(projects)


@client_bp.patch("/projects/<int:pid>/status")
@require_role("client", "admin", "staff")
def update_project_status(pid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    conn = db()
    try:
        if g.user["role"] == "client":
            member = conn.execute(
                "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='client'",
                (pid, g.user["id"]),
            ).fetchone()
            if not member:
                return jsonify({"error": "Forbidden"}), 403

        row = conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404

        conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Status updated"})


@client_bp.get("/requests")
@require_role("client", "admin", "staff")
def my_requests():
    conn = db()
    client_id = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    try:
        rows = conn.execute(
            "SELECT * FROM service_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 50",
            (client_id,),
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@client_bp.post("/requests")
@require_role("client")
def create_request():
    data = request.get_json(silent=True) or {}
    req_type = data.get("type")
    prompt = (data.get("prompt") or "").strip()
    project_id = data.get("project_id")

    if req_type not in ("content", "chat", "file"):
        return jsonify({"error": "type must be content, chat, or file"}), 400
    if not prompt:
        return jsonify({"error": "prompt required"}), 400

    conn = db()
    try:
        cur = conn.execute(
            "INSERT INTO service_requests (client_id, project_id, type, prompt) VALUES (?, ?, ?, ?)",
            (g.user["id"], project_id, req_type, prompt),
        )
        conn.commit()
        rid = cur.lastrowid

        notify = []
        if project_id:
            # Notify all staff members on the project
            staff_rows = conn.execute("""
                SELECT u.email FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                WHERE pm.project_id = ? AND pm.role = 'staff'
            """, (project_id,)).fetchall()
            notify = [r["email"] for r in staff_rows]
        if Config.NOTIFY_ADMIN_EMAIL and Config.NOTIFY_ADMIN_EMAIL not in notify:
            notify.append(Config.NOTIFY_ADMIN_EMAIL)
    finally:
        conn.close()

    email_service.notify_new_request(
        client_name=g.user["name"],
        req_type=req_type,
        prompt=prompt,
        request_id=rid,
        notify_emails=notify,
    )

    return jsonify({"id": rid, "message": "Request submitted"}), 201


@client_bp.get("/conversations")
@require_role("client", "admin")
def list_conversations():
    conn = db()
    client_id = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE client_id=? ORDER BY updated_at DESC",
            (client_id,),
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])
