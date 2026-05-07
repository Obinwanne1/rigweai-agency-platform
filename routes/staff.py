import sqlite3
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from config import Config

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")

VALID_STATUSES = ("active", "assigned", "work_in_progress", "completed", "paused", "cancelled")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@staff_bp.get("/projects")
@require_role("admin", "staff")
def my_projects():
    conn = db()
    try:
        if g.user["role"] == "admin":
            rows = conn.execute("""
                SELECT p.*, c.name as client_name
                FROM projects p
                LEFT JOIN users c ON c.id = p.client_id
                ORDER BY p.created_at DESC
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT DISTINCT p.*, c.name as client_name
                FROM projects p
                LEFT JOIN users c ON c.id = p.client_id
                JOIN project_members pm ON pm.project_id = p.id
                WHERE pm.user_id = ? AND pm.role = 'staff'
                ORDER BY p.created_at DESC
            """, (g.user["id"],)).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@staff_bp.patch("/projects/<int:pid>/status")
@require_role("admin", "staff")
def update_project_status(pid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    conn = db()
    try:
        if g.user["role"] == "staff":
            member = conn.execute(
                "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
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


@staff_bp.get("/projects/<int:pid>/requests")
@require_role("admin", "staff")
def project_requests(pid):
    conn = db()
    try:
        if g.user["role"] == "staff":
            member = conn.execute(
                "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
                (pid, g.user["id"]),
            ).fetchone()
            if not member:
                return jsonify({"error": "Forbidden"}), 403
        rows = conn.execute(
            "SELECT * FROM service_requests WHERE project_id=? ORDER BY created_at DESC", (pid,)
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@staff_bp.patch("/requests/<int:rid>")
@require_role("admin", "staff")
def update_request(rid):
    conn = db()
    try:
        req_row = conn.execute("SELECT * FROM service_requests WHERE id=?", (rid,)).fetchone()
        if not req_row:
            return jsonify({"error": "Not found"}), 404

        if g.user["role"] == "staff" and req_row["project_id"]:
            member = conn.execute(
                "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
                (req_row["project_id"], g.user["id"]),
            ).fetchone()
            if not member:
                return jsonify({"error": "Forbidden"}), 403

        data = request.get_json(silent=True) or {}
        fields, vals = [], []
        if "status" in data and data["status"] in ("pending", "in_progress", "completed", "failed"):
            fields.append("status=?"); vals.append(data["status"])
        if "output_text" in data:
            fields.append("output_text=?"); vals.append(data["output_text"])

        if fields:
            vals.append(rid)
            conn.execute(f"UPDATE service_requests SET {', '.join(fields)} WHERE id=?", vals)
            conn.commit()

        client_row = None
        if data.get("status") == "completed":
            client_row = conn.execute(
                "SELECT u.email, u.name FROM users u JOIN service_requests sr ON sr.client_id = u.id WHERE sr.id=?",
                (rid,),
            ).fetchone()
            client_row = dict(client_row) if client_row else None
    finally:
        conn.close()

    if client_row:
        email_service.notify_request_completed(
            client_email=client_row["email"],
            client_name=client_row["name"],
            req_type=dict(req_row)["type"],
            request_id=rid,
        )

    return jsonify({"message": "Updated"})
