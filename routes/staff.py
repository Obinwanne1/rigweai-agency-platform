import sqlite3
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from config import Config

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@staff_bp.get("/projects")
@require_role("admin", "staff")
def my_projects():
    conn = db()
    if g.user["role"] == "admin":
        rows = conn.execute("""
            SELECT p.*, c.name as client_name, s.name as staff_name
            FROM projects p
            LEFT JOIN users c ON c.id = p.client_id
            LEFT JOIN users s ON s.id = p.staff_id
            ORDER BY p.created_at DESC
        """).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.*, c.name as client_name, s.name as staff_name
            FROM projects p
            LEFT JOIN users c ON c.id = p.client_id
            LEFT JOIN users s ON s.id = p.staff_id
            WHERE p.staff_id = ?
            ORDER BY p.created_at DESC
        """, (g.user["id"],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@staff_bp.get("/projects/<int:pid>/requests")
@require_role("admin", "staff")
def project_requests(pid):
    conn = db()
    if g.user["role"] == "staff":
        proj = conn.execute(
            "SELECT id FROM projects WHERE id=? AND staff_id=?", (pid, g.user["id"])
        ).fetchone()
        if not proj:
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
    rows = conn.execute(
        "SELECT * FROM service_requests WHERE project_id=? ORDER BY created_at DESC", (pid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@staff_bp.patch("/requests/<int:rid>")
@require_role("admin", "staff")
def update_request(rid):
    conn = db()
    req_row = conn.execute("SELECT * FROM service_requests WHERE id=?", (rid,)).fetchone()
    if not req_row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    if g.user["role"] == "staff" and req_row["project_id"]:
        proj = conn.execute(
            "SELECT id FROM projects WHERE id=? AND staff_id=?",
            (req_row["project_id"], g.user["id"]),
        ).fetchone()
        if not proj:
            conn.close()
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

    # Email client when marked completed
    if data.get("status") == "completed":
        client_row = conn.execute(
            "SELECT u.email, u.name FROM users u JOIN service_requests sr ON sr.client_id = u.id WHERE sr.id=?",
            (rid,),
        ).fetchone()
        if client_row:
            email_service.notify_request_completed(
                client_email=client_row["email"],
                client_name=client_row["name"],
                req_type=dict(req_row)["type"],
                request_id=rid,
            )

    conn.close()
    return jsonify({"message": "Updated"})
