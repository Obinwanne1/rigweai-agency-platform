import re
from flask import Flask, send_from_directory, redirect, abort, render_template
from flask_cors import CORS
from jinja2 import TemplateNotFound
from config import Config

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = Config.UPLOAD_MAX_BYTES
CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

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


@app.get("/")
def index():
    return redirect("/login")


@app.get("/login")
def login_page():
    from flask import render_template
    return render_template("login.html")


@app.get("/dashboard")
def dashboard():
    from flask import render_template
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
    from flask import render_template
    return render_template("profile.html")


@app.get("/forgot-password")
def forgot_password_page():
    from flask import render_template
    return render_template("forgot-password.html")


@app.get("/reset-password")
def reset_password_page():
    from flask import render_template
    return render_template("reset-password.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
