from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import email_service
from services.db import get_db, project_members, VALID_STATUSES

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


@staff_bp.get("/projects")
@require_role("admin", "staff")
def my_projects():
    conn = get_db()
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
    result = []
    for r in rows:
        p = dict(r)
        p["members"] = project_members(conn, p["id"])
        result.append(p)
    return jsonify(result)


@staff_bp.patch("/projects/<int:pid>/status")
@require_role("admin", "staff")
def update_project_status(pid):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    conn = get_db()
    if g.user["role"] == "staff":
        if not conn.execute(
            "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
            (pid, g.user["id"]),
        ).fetchone():
            return jsonify({"error": "Forbidden"}), 403

    if not conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
        return jsonify({"error": "Not found"}), 404

    conn.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))
    conn.commit()
    return jsonify({"message": "Status updated"})


@staff_bp.get("/projects/<int:pid>/requests")
@require_role("admin", "staff")
def project_requests(pid):
    conn = get_db()
    if g.user["role"] == "staff":
        if not conn.execute(
            "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
            (pid, g.user["id"]),
        ).fetchone():
            return jsonify({"error": "Forbidden"}), 403
    rows = conn.execute(
        "SELECT * FROM service_requests WHERE project_id=? ORDER BY created_at DESC", (pid,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@staff_bp.patch("/requests/<int:rid>")
@require_role("admin", "staff")
def update_request(rid):
    conn = get_db()
    req_row = conn.execute("SELECT * FROM service_requests WHERE id=?", (rid,)).fetchone()
    if not req_row:
        return jsonify({"error": "Not found"}), 404

    if g.user["role"] == "staff":
        if not req_row["project_id"]:
            return jsonify({"error": "Forbidden"}), 403
        if not conn.execute(
            "SELECT id FROM project_members WHERE project_id=? AND user_id=? AND role='staff'",
            (req_row["project_id"], g.user["id"]),
        ).fetchone():
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

    if client_row:
        email_service.notify_request_completed(
            client_email=client_row["email"],
            client_name=client_row["name"],
            req_type=dict(req_row)["type"],
            request_id=rid,
        )

    return jsonify({"message": "Updated"})
