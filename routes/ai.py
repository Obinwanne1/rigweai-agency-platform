import sqlite3
import json
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import claude_service, file_service
from config import Config

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@ai_bp.post("/generate")
@require_role("client", "staff", "admin")
def generate():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    context = (data.get("context") or "").strip()

    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    if len(prompt) > 4000:
        return jsonify({"error": "prompt too long (max 4000 chars)"}), 400

    try:
        output = claude_service.generate_content(prompt, context)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Log as service_request
    conn = db()
    conn.execute(
        "INSERT INTO service_requests (client_id, type, prompt, status, output_text) VALUES (?,?,?,?,?)",
        (g.user["id"], "content", prompt, "completed", output),
    )
    conn.commit()
    conn.close()
    return jsonify({"output": output})


@ai_bp.post("/chat")
@require_role("client", "staff", "admin")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({"error": "message required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "message too long (max 2000 chars)"}), 400

    conn = db()
    history = []

    if conversation_id:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id=? AND client_id=?",
            (conversation_id, g.user["id"]),
        ).fetchone()
        if row:
            history = json.loads(row["messages"])

    try:
        reply = claude_service.chat(history, message)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    # Keep last 40 messages to avoid token bloat
    history = history[-40:]

    if conversation_id and conn.execute(
        "SELECT id FROM conversations WHERE id=? AND client_id=?", (conversation_id, g.user["id"])
    ).fetchone():
        conn.execute(
            "UPDATE conversations SET messages=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(history), conversation_id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO conversations (client_id, messages) VALUES (?,?)",
            (g.user["id"], json.dumps(history)),
        )
        conversation_id = cur.lastrowid

    conn.commit()
    conn.close()
    return jsonify({"reply": reply, "conversation_id": conversation_id})


@ai_bp.post("/process-file")
@require_role("client", "staff", "admin")
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400

    file = request.files["file"]
    instruction = (request.form.get("instruction") or "Analyze and summarize this file.").strip()

    if not file_service.allowed(file.filename):
        return jsonify({"error": f"File type not allowed"}), 400

    try:
        file_info = file_service.save_upload(file, g.user["id"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Save file record
    conn = db()
    cur = conn.execute(
        "INSERT INTO files (user_id, filename, original_name, file_type, size, path) VALUES (?,?,?,?,?,?)",
        (file_info["user_id"], file_info["filename"], file_info["original_name"],
         file_info["file_type"], file_info["size"], file_info["path"]),
    )
    conn.commit()
    file_id = cur.lastrowid

    try:
        text, img_b64, media_type = file_service.extract_text(file_info)
        output = claude_service.analyze_file(text, instruction, img_b64, media_type)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    conn.execute(
        "INSERT INTO service_requests (client_id, type, prompt, file_id, status, output_text) VALUES (?,?,?,?,?,?)",
        (g.user["id"], "file", instruction, file_id, "completed", output),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "output": output,
        "file": {
            "id": file_id,
            "original_name": file_info["original_name"],
            "file_type": file_info["file_type"],
            "size": file_info["size"],
        },
    })
