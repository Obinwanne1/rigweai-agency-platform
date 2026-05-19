import re as _re
import secrets
import datetime
import logging
from flask import Blueprint, request, jsonify, make_response, g
from services.auth_service import verify_password, create_token, hash_password
from services.db import get_db
from middleware.auth_middleware import require_role
from extensions import limiter
from config import Config

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_MAX_FAILED = 5
_LOCKOUT_MINUTES = 15

# Compiled once at import time
_RE_UPPER   = _re.compile(r"[A-Z]")
_RE_LOWER   = _re.compile(r"[a-z]")
_RE_DIGIT   = _re.compile(r"\d")
_RE_SPECIAL = _re.compile(r"[^A-Za-z0-9]")


def _validate_password_strength(pw: str) -> str | None:
    if len(pw) < 8:
        return "Password must be at least 8 characters"
    if not _RE_UPPER.search(pw):
        return "Password must contain at least one uppercase letter"
    if not _RE_LOWER.search(pw):
        return "Password must contain at least one lowercase letter"
    if not _RE_DIGIT.search(pw):
        return "Password must contain at least one number"
    if not _RE_SPECIAL.search(pw):
        return "Password must contain at least one special character (!@#$%^&* etc.)"
    return None


def _get_user_by_email(email: str):
    row = get_db().execute(
        "SELECT id, email, name, role, password_hash, is_active, "
        "must_change_password, failed_attempts, locked_until "
        "FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    return dict(row) if row else None


def _increment_failed(user_id: int, current_count: int) -> None:
    new_count = current_count + 1
    locked_until = None
    if new_count >= _MAX_FAILED:
        locked_until = (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=_LOCKOUT_MINUTES)
        ).isoformat()
    conn = get_db()
    conn.execute(
        "UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
        (new_count, locked_until, user_id),
    )
    conn.commit()


def _reset_failed(user_id: int) -> None:
    conn = get_db()
    conn.execute(
        "UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=?",
        (user_id,),
    )
    conn.commit()


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

    if user.get("locked_until"):
        lock_dt = datetime.datetime.fromisoformat(user["locked_until"])
        if datetime.datetime.now(datetime.timezone.utc) < lock_dt:
            return jsonify({
                "error": f"Account locked after {_MAX_FAILED} failed attempts. "
                         f"Try again in {_LOCKOUT_MINUTES} minutes."
            }), 429
        _reset_failed(user["id"])

    if not verify_password(password, user["password_hash"]):
        _increment_failed(user["id"], user.get("failed_attempts", 0))
        return jsonify({"error": "Invalid credentials"}), 401

    _reset_failed(user["id"])

    token = create_token(user["id"], user["role"])
    resp = make_response(
        jsonify({
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "role": user["role"],
                "email": user["email"],
                "must_change_password": bool(user.get("must_change_password")),
            },
        })
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

    err = _validate_password_strength(new_pw)
    if err:
        return jsonify({"error": err}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id=?", (g.user["id"],)
    ).fetchone()
    if not row or not verify_password(current, row["password_hash"]):
        return jsonify({"error": "Current password is incorrect"}), 401
    conn.execute(
        "UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?",
        (hash_password(new_pw), g.user["id"]),
    )
    conn.commit()
    return jsonify({"message": "Password changed successfully"})


@auth_bp.post("/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE email=? AND is_active=1",
        (email,),
    ).fetchone()
    if user:
        conn.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE user_id=? AND used=0",
            (user["id"],),
        )
        token = secrets.token_hex(32)
        expires = (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(hours=1)
        ).isoformat()
        conn.execute(
            "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user["id"], token, expires),
        )
        conn.commit()
        from services.email_service import send_password_reset
        email_sent = send_password_reset(user["email"], user["name"], token)
        if not email_sent:
            admin = Config.NOTIFY_ADMIN_EMAIL or "your administrator"
            return jsonify({"message": "no_email", "admin": admin})

    # Always return sent-style to prevent email enumeration
    return jsonify({"message": "sent"})


@auth_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_pw = data.get("new_password") or ""

    if not token or not new_pw:
        return jsonify({"error": "token and new_password required"}), 400

    err = _validate_password_strength(new_pw)
    if err:
        return jsonify({"error": err}), 400

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM password_reset_tokens WHERE token=? AND used=0",
        (token,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Invalid or already-used reset link"}), 400

    expires = datetime.datetime.fromisoformat(row["expires_at"])
    if datetime.datetime.now(datetime.timezone.utc) > expires:
        return jsonify({"error": "Reset link has expired. Request a new one."}), 400

    conn.execute(
        "UPDATE users SET password_hash=?, must_change_password=0, "
        "failed_attempts=0, locked_until=NULL WHERE id=?",
        (hash_password(new_pw), row["user_id"]),
    )
    conn.execute(
        "UPDATE password_reset_tokens SET used=1 WHERE id=?", (row["id"],)
    )
    conn.commit()
    return jsonify({"message": "Password reset successfully. You can now log in."})
