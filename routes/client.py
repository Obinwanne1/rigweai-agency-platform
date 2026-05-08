from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from services.db import get_db, project_members, VALID_STATUSES
from config import Config

client_bp = Blueprint("client", __name__, url_prefix="/api/client")


@client_bp.get("/projects")
@require_role("client", "admin", "staff")
def my_projects():
    conn = get_db()
    uid = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    rows = conn.execute("""
        SELECT DISTINCT p.*
        FROM projects p
        JOIN project_members pm ON pm.project_id = p.id
        WHERE pm.user_id = ? AND pm.role = 'client'
        ORDER BY p.created_at DESC
    """, (uid,)).fetchall()
    result = []
    for r in rows:
        p = dict(r)
        p["members"] = project_members(conn, p["id"])
        result.append(p)
    return jsonify(result)


@client_bp.patch("/projects/<int:pid>/status")
@require_role("client", "admin", "staff")
def update_project_status(pid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    conn = get_db()
    if g.user["role"] == "client":
        if not conn.execute(
            "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='client'",
            (pid, g.user["id"]),
        ).fetchone():
            return jsonify({"error": "Forbidden"}), 403

    if not conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
        return jsonify({"error": "Not found"}), 404

    conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))
    conn.commit()
    return jsonify({"message": "Status updated"})


@client_bp.get("/requests")
@require_role("client", "admin", "staff")
def my_requests():
    conn = get_db()
    client_id = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    rows = conn.execute(
        "SELECT * FROM service_requests WHERE client_id=? ORDER BY created_at DESC LIMIT 50",
        (client_id,),
    ).fetchall()
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

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO service_requests (client_id, project_id, type, prompt) VALUES (?, ?, ?, ?)",
        (g.user["id"], project_id, req_type, prompt),
    )
    conn.commit()
    rid = cur.lastrowid

    notify = []
    if project_id:
        staff_rows = conn.execute("""
            SELECT u.email FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.project_id = ? AND pm.role = 'staff'
        """, (project_id,)).fetchall()
        notify = [r["email"] for r in staff_rows]
    if Config.NOTIFY_ADMIN_EMAIL and Config.NOTIFY_ADMIN_EMAIL not in notify:
        notify.append(Config.NOTIFY_ADMIN_EMAIL)

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
    conn = get_db()
    client_id = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE client_id=? ORDER BY updated_at DESC",
        (client_id,),
    ).fetchall()
    return jsonify([dict(r) for r in rows])
