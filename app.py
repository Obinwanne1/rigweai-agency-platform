from flask import Flask, send_from_directory, redirect
from flask_cors import CORS
from config import Config

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = Config.UPLOAD_MAX_BYTES
CORS(app, supports_credentials=True)

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


@app.get("/admin/<path:page>")
def admin_pages(page):
    from flask import render_template
    return render_template(f"admin/{page}.html")


@app.get("/staff/<path:page>")
def staff_pages(page):
    from flask import render_template
    return render_template(f"staff/{page}.html")


@app.get("/client/<path:page>")
def client_pages(page):
    from flask import render_template
    return render_template(f"client/{page}.html")


@app.get("/profile")
def profile_page():
    from flask import render_template
    return render_template("profile.html")


@app.get("/forgot-password")
def forgot_password_page():
    from flask import render_template
    return render_template("forgot-password.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
