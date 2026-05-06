import sqlite3
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from config import Config

client_bp = Blueprint("client", __name__, url_prefix="/api/client")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@client_bp.get("/projects")
@require_role("client", "admin", "staff")
def my_projects():
    conn = db()
    client_id = g.user["id"] if g.user["role"] == "client" else request.args.get("client_id", g.user["id"])
    try:
        rows = conn.execute("""
            SELECT p.*, s.name as staff_name
            FROM projects p
            LEFT JOIN users s ON s.id = p.staff_id
            WHERE p.client_id = ?
            ORDER BY p.created_at DESC
        """, (client_id,)).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


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
            row = conn.execute(
                "SELECT s.email FROM projects p JOIN users s ON s.id = p.staff_id WHERE p.id=? AND p.staff_id IS NOT NULL",
                (project_id,),
            ).fetchone()
            if row:
                notify.append(row["email"])
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
