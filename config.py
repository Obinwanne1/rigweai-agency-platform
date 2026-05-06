import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    JWT_EXPIRY_HOURS = 24
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", 5000))
    UPLOAD_MAX_BYTES = int(os.getenv("UPLOAD_MAX_MB", 10)) * 1024 * 1024
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
    DB_PATH = os.path.join(os.path.dirname(__file__), "agency.db")
    ALLOWED_EXTENSIONS = {"pdf", "txt", "docx", "png", "jpg", "jpeg", "csv"}
    CLAUDE_MODEL = "claude-sonnet-4-6"
    DEBUG = FLASK_ENV == "development"
