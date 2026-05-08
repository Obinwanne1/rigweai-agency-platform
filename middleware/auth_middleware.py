from functools import wraps
from flask import request, jsonify, g
from services.auth_service import decode_token
from services.db import get_db
import jwt


def _get_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("token")


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _get_token()
            if not token:
                return jsonify({"error": "Authentication required"}), 401
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            if roles and payload["role"] not in roles:
                return jsonify({"error": "Forbidden"}), 403

            conn = get_db()
            row = conn.execute(
                "SELECT id, email, name, role, is_active, must_change_password FROM users WHERE id = ?",
                (int(payload["sub"]),),
            ).fetchone()

            if not row or not row["is_active"]:
                return jsonify({"error": "Account inactive or not found"}), 401

            g.user = dict(row)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
