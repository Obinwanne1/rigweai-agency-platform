import sqlite3
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services.auth_service import hash_password
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Stats ──────────────────────────────────────────────────────────────
@admin_bp.get("/stats")
@require_role("admin", "staff")
def stats():
    conn = db()
    data = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "clients": conn.execute("SELECT COUNT(*) FROM users WHERE role='client'").fetchone()[0],
        "staff": conn.execute("SELECT COUNT(*) FROM users WHERE role='staff'").fetchone()[0],
        "projects": conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
        "requests": conn.execute("SELECT COUNT(*) FROM service_requests").fetchone()[0],
        "pending_requests": conn.execute("SELECT COUNT(*) FROM service_requests WHERE status='pending'").fetchone()[0],
    }
    conn.close()
    return jsonify(data)


# ── Users ──────────────────────────────────────────────────────────────
@admin_bp.get("/users")
@require_role("admin", "staff")
def list_users():
    conn = db()
    rows = conn.execute(
        "SELECT id, email, name, role, is_active, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
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

    conn = db()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)",
            (email, hash_password(password), name, role),
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already exists"}), 409
    conn.close()
    return jsonify({"id": user_id, "message": "User created"}), 201


@admin_bp.patch("/users/<int:uid>")
@require_role("admin")
def update_user(uid):
    data = request.get_json(silent=True) or {}
    conn = db()
    row = conn.execute("SELECT id FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    fields, vals = [], []
    if "name" in data:
        fields.append("name=?"); vals.append(data["name"].strip())
    if "role" in data and data["role"] in ("admin", "staff", "client"):
        fields.append("role=?"); vals.append(data["role"])
    if "is_active" in data:
        fields.append("is_active=?"); vals.append(1 if data["is_active"] else 0)
    if "password" in data and data["password"]:
        fields.append("password_hash=?"); vals.append(hash_password(data["password"]))

    if fields:
        vals.append(uid)
        conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})


@admin_bp.delete("/users/<int:uid>")
@require_role("admin")
def delete_user(uid):
    if uid == g.user["id"]:
        return jsonify({"error": "Cannot delete yourself"}), 400
    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})


# ── Projects ───────────────────────────────────────────────────────────
@admin_bp.get("/projects")
@require_role("admin", "staff")
def list_projects():
    conn = db()
    rows = conn.execute("""
        SELECT p.*,
               c.name as client_name, c.email as client_email,
               s.name as staff_name
        FROM projects p
        LEFT JOIN users c ON c.id = p.client_id
        LEFT JOIN users s ON s.id = p.staff_id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@admin_bp.post("/projects")
@require_role("admin", "staff")
def create_project():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    client_id = data.get("client_id")
    description = (data.get("description") or "").strip()
    staff_id = data.get("staff_id")

    if not title or not client_id:
        return jsonify({"error": "title and client_id required"}), 400

    conn = db()
    cur = conn.execute(
        "INSERT INTO projects (client_id, staff_id, title, description) VALUES (?, ?, ?, ?)",
        (client_id, staff_id, title, description),
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return jsonify({"id": pid, "message": "Project created"}), 201


@admin_bp.patch("/projects/<int:pid>")
@require_role("admin", "staff")
def update_project(pid):
    data = request.get_json(silent=True) or {}
    conn = db()
    row = conn.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    fields, vals = [], []
    for col in ("title", "description", "status", "staff_id"):
        if col in data:
            fields.append(f"{col}=?"); vals.append(data[col])

    if fields:
        vals.append(pid)
        conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({"message": "Updated"})


@admin_bp.delete("/projects/<int:pid>")
@require_role("admin")
def delete_project(pid):
    conn = db()
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})


# ── Requests (admin view) ──────────────────────────────────────────────
@admin_bp.get("/requests")
@require_role("admin", "staff")
def list_requests():
    conn = db()
    rows = conn.execute("""
        SELECT sr.*, u.name as client_name, p.title as project_title
        FROM service_requests sr
        LEFT JOIN users u ON u.id = sr.client_id
        LEFT JOIN projects p ON p.id = sr.project_id
        ORDER BY sr.created_at DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
