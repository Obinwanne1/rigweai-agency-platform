import os
import uuid
import base64
import csv
import logging
from werkzeug.utils import secure_filename
from config import Config

log = logging.getLogger(__name__)

ALLOWED = Config.ALLOWED_EXTENSIONS
_PDF_TEXT_CAP = 50_000   # chars — ~35 pages of dense text
_IMG_SIZE_CAP = 5 * 1024 * 1024  # 5 MB — refuse base64 encoding beyond this


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def allowed(filename: str) -> bool:
    return _ext(filename) in ALLOWED


def save_upload(file_storage, user_id: int) -> dict:
    original = file_storage.filename
    if not allowed(original):
        raise ValueError(f"File type not allowed. Allowed: {', '.join(ALLOWED)}")

    ext = _ext(original)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(Config.UPLOAD_DIR, unique_name)

    # Validate path stays within upload dir (path traversal guard)
    real_upload_dir = os.path.realpath(Config.UPLOAD_DIR)
    real_path = os.path.realpath(path)
    if not real_path.startswith(real_upload_dir + os.sep):
        raise ValueError("Invalid file path")

    file_storage.save(path)
    size = os.path.getsize(path)

    return {
        "filename": unique_name,
        "original_name": secure_filename(original),
        "file_type": ext,
        "size": size,
        "path": path,
        "user_id": user_id,
    }


def extract_text(file_info: dict) -> tuple[str, str | None, str | None]:
    """Returns (text, image_b64, media_type). For images, text is empty."""
    path = file_info["path"]
    ext = file_info["file_type"]

    if ext == "pdf":
        import pdfplumber
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
                if len(text) >= _PDF_TEXT_CAP:
                    text = text[:_PDF_TEXT_CAP]
                    break
        return text, None, None

    if ext == "docx":
        from docx import Document
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text[:_PDF_TEXT_CAP], None, None

    if ext == "txt":
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(_PDF_TEXT_CAP), None, None

    if ext == "csv":
        with open(path, encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.reader(f)
            rows = [",".join(row) for row in reader]
        return "\n".join(rows)[:_PDF_TEXT_CAP], None, None

    if ext in ("png", "jpg", "jpeg"):
        size = os.path.getsize(path)
        if size > _IMG_SIZE_CAP:
            raise ValueError(f"Image too large for analysis (max {_IMG_SIZE_CAP // (1024*1024)} MB)")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return "", b64, mime

    raise ValueError(f"Cannot extract text from .{ext}")
