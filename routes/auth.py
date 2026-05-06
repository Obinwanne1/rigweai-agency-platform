import sqlite3
from flask import Blueprint, request, jsonify, make_response, g
from services.auth_service import verify_password, create_token, hash_password
from middleware.auth_middleware import require_role
from config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _get_user_by_email(email: str):
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, email, name, role, password_hash, is_active FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = _get_user_by_email(email)
    if not user or not user["is_active"]:
        return jsonify({"error": "Invalid credentials"}), 401
    if not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user["id"], user["role"])
    resp = make_response(
        jsonify({"token": token, "user": {"id": user["id"], "name": user["name"], "role": user["role"], "email": user["email"]}})
    )
    resp.set_cookie(
        "token", token,
        httponly=True,
        samesite="Lax",
        secure=not Config.DEBUG,
        max_age=Config.JWT_EXPIRY_HOURS * 3600,
    )
    return resp


@auth_bp.post("/logout")
def logout():
    resp = make_response(jsonify({"message": "Logged out"}))
    resp.delete_cookie("token")
    return resp


@auth_bp.get("/me")
@require_role()
def me():
    return jsonify(g.user)


@auth_bp.post("/change-password")
@require_role()
def change_password():
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_pw = data.get("new_password") or ""

    if not current or not new_pw:
        return jsonify({"error": "current_password and new_password required"}), 400
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id=?", (g.user["id"],)).fetchone()
        if not row or not verify_password(current, row["password_hash"]):
            return jsonify({"error": "Current password is incorrect"}), 401
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new_pw), g.user["id"]))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Password changed successfully"})
