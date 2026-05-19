from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services.auth_service import hash_password
from services.db import get_db, bulk_project_members

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

_VALID_USER_FIELDS = {"name", "role", "is_active", "password"}
_VALID_PROJECT_FIELDS = {"title", "description", "status"}
_VALID_STATUSES = ("active", "assigned", "work_in_progress", "completed", "paused", "cancelled")


# ── Stats ──────────────────────────────────────────────────────────────
@admin_bp.get("/stats")
@require_role("admin", "staff")
def stats():
    conn = get_db()
    row = conn.execute("""
        SELECT
            COUNT(*) AS users,
            SUM(role = 'client') AS clients,
            SUM(role = 'staff') AS staff
        FROM users
    """).fetchone()
    proj = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    reqs = conn.execute("SELECT COUNT(*), SUM(status='pending') FROM service_requests").fetchone()
    return jsonify({
        "users": row["users"],
        "clients": row["clients"],
        "staff": row["staff"],
        "projects": proj,
        "requests": reqs[0],
        "pending_requests": reqs[1] or 0,
    })


# ── Users ──────────────────────────────────────────────────────────────
@admin_bp.get("/users")
@require_role("admin", "staff")
def list_users():
    rows = get_db().execute(
        "SELECT id, email, name, role, is_active, created_at FROM users ORDER BY created_at DESC LIMIT 500"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@admin_bp.post("/users")
@require_role("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    role = data.get("role")
    password = data.get("password") or ""

    if not all([email, name, role, password]):
        return jsonify({"error": "email, name, role, password required"}), 400
    if role not in ("admin", "staff", "client"):
        return jsonify({"error": "Invalid role"}), 400

    import sqlite3
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, name, role, must_change_password) VALUES (?, ?, ?, ?, 1)",
            (email, hash_password(password), name, role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 409
    return jsonify({"id": cur.lastrowid, "message": "User created"}), 201


@admin_bp.patch("/users/<int:uid>")
@require_role("admin")
def update_user(uid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    if not conn.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone():
        return jsonify({"error": "User not found"}), 404

    # Explicit field mapping — never interpolate arbitrary keys
    fields, vals = [], []
    if "name" in data:
        fields.append("name=?"); vals.append(str(data["name"]).strip())
    if "role" in data and data["role"] in ("admin", "staff", "client"):
        fields.append("role=?"); vals.append(data["role"])
    if "is_active" in data:
        fields.append("is_active=?"); vals.append(1 if data["is_active"] else 0)
    if "password" in data and data["password"]:
        fields.append("password_hash=?"); vals.append(hash_password(data["password"]))
        fields.append("must_change_password=?"); vals.append(1)

    if fields:
        vals.append(uid)
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    return jsonify({"message": "Updated"})


@admin_bp.delete("/users/<int:uid>")
@require_role("admin")
def delete_user(uid):
    if uid == g.user["id"]:
        return jsonify({"error": "Cannot delete yourself"}), 400
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    return jsonify({"message": "Deleted"})


# ── Projects ───────────────────────────────────────────────────────────
@admin_bp.get("/projects")
@require_role("admin", "staff")
def list_projects():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.client_id, p.title, p.description, p.status,
               p.created_at, p.updated_at,
               c.name as client_name, c.email as client_email
        FROM projects p
        LEFT JOIN users c ON c.id = p.client_id
        ORDER BY p.created_at DESC
        LIMIT 200
    """).fetchall()
    projects = [dict(r) for r in rows]
    members_map = bulk_project_members(conn, [p["id"] for p in projects])
    for p in projects:
        p["members"] = members_map.get(p["id"], [])
    return jsonify(projects)


@admin_bp.post("/projects")
@require_role("admin", "staff")
def create_project():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    client_id = data.get("client_id")
    description = (data.get("description") or "").strip()
    member_ids = data.get("member_ids") or []

    if not title or not client_id:
        return jsonify({"error": "title and client_id required"}), 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO projects (client_id, title, description) VALUES (?, ?, ?)",
        (client_id, title, description),
    )
    pid = cur.lastrowid
    conn.execute(
        "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, 'client')",
        (pid, client_id),
    )
    for m in member_ids:
        uid = m.get("user_id")
        role = m.get("role", "staff")
        if uid and role in ("client", "staff"):
            conn.execute(
                "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
                (pid, uid, role),
            )
    conn.commit()
    return jsonify({"id": pid, "message": "Project created"}), 201


@admin_bp.patch("/projects/<int:pid>")
@require_role("admin", "staff")
def update_project(pid):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
        return jsonify({"error": "Not found"}), 404

    # Explicit field mapping — no user-key interpolation
    fields, vals = [], []
    if "title" in data:
        fields.append("title=?"); vals.append(str(data["title"]))
    if "description" in data:
        fields.append("description=?"); vals.append(str(data["description"]))
    if "status" in data and data["status"] in _VALID_STATUSES:
        fields.append("status=?"); vals.append(data["status"])

    if fields:
        vals.append(pid)
        conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    return jsonify({"message": "Updated"})


@admin_bp.post("/projects/<int:pid>/members")
@require_role("admin", "staff")
def add_member(pid):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    role = data.get("role", "staff")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    if role not in ("client", "staff"):
        return jsonify({"error": "role must be client or staff"}), 400

    conn = get_db()
    if not conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone():
        return jsonify({"error": "Project not found"}), 404
    if not conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
        return jsonify({"error": "User not found"}), 404
    conn.execute(
        "INSERT OR IGNORE INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
        (pid, user_id, role),
    )
    conn.commit()
    return jsonify({"message": "Member added"}), 201


@admin_bp.delete("/projects/<int:pid>/members/<int:uid>")
@require_role("admin", "staff")
def remove_member(pid, uid):
    conn = get_db()
    conn.execute(
        "DELETE FROM project_members WHERE project_id=? AND user_id=?", (pid, uid)
    )
    conn.commit()
    return jsonify({"message": "Member removed"})


@admin_bp.delete("/projects/<int:pid>")
@require_role("admin")
def delete_project(pid):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit()
    return jsonify({"message": "Deleted"})


# ── Requests (admin view) ──────────────────────────────────────────────
@admin_bp.get("/requests")
@require_role("admin", "staff")
def list_requests():
    rows = get_db().execute("""
        SELECT sr.*, u.name as client_name, p.title as project_title
        FROM service_requests sr
        LEFT JOIN users u ON u.id = sr.client_id
        LEFT JOIN projects p ON p.id = sr.project_id
        ORDER BY sr.created_at DESC
        LIMIT 100
    """).fetchall()
    return jsonify([dict(r) for r in rows])
