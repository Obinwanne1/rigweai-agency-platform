import re
from flask import Flask, redirect, abort, render_template, jsonify
from flask_cors import CORS
from jinja2 import TemplateNotFound
from config import Config
from extensions import limiter
from services.db import close_db, get_db

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = Config.UPLOAD_MAX_BYTES
CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)
limiter.init_app(app)
app.teardown_appcontext(close_db)

# Register blueprints
from routes.auth import auth_bp
app.register_blueprint(auth_bp)

from routes.admin import admin_bp
app.register_blueprint(admin_bp)

from routes.staff import staff_bp
app.register_blueprint(staff_bp)

from routes.client import client_bp
app.register_blueprint(client_bp)

from routes.ai import ai_bp
app.register_blueprint(ai_bp)


# ── Security headers ───────────────────────────────────────────────────

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "   # inline scripts in templates
    "style-src 'self' 'unsafe-inline'; "    # inline styles in templates
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)

@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = _CSP
    if not Config.DEBUG:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# ── Health check ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    try:
        get_db().execute("SELECT 1").fetchone()
        db_ok = True
    except Exception:
        db_ok = False
    status = "ok" if db_ok else "degraded"
    return jsonify({"status": status, "db": db_ok}), 200 if db_ok else 503


# ── Page routes ────────────────────────────────────────────────────────

@app.get("/")
def index():
    return redirect("/login")


@app.get("/login")
def login_page():
    return render_template("login.html")


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard_router.html")


def _safe_page(page: str) -> str:
    """Allow only simple alphanumeric page names — no path traversal."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", page):
        abort(404)
    return page


@app.get("/admin/<path:page>")
def admin_pages(page):
    try:
        return render_template(f"admin/{_safe_page(page)}.html")
    except TemplateNotFound:
        abort(404)


@app.get("/staff/<path:page>")
def staff_pages(page):
    try:
        return render_template(f"staff/{_safe_page(page)}.html")
    except TemplateNotFound:
        abort(404)


@app.get("/client/<path:page>")
def client_pages(page):
    try:
        return render_template(f"client/{_safe_page(page)}.html")
    except TemplateNotFound:
        abort(404)


@app.get("/profile")
def profile_page():
    return render_template("profile.html")


@app.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot-password.html")


@app.get("/reset-password")
def reset_password_page():
    return render_template("reset-password.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
