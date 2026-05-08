import os
import json
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_role
from services import claude_service, file_service
from services.db import get_db
from extensions import limiter
from config import Config

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.get("/conversations/<int:cid>")
@require_role("client", "staff", "admin")
def get_conversation(cid):
    conn = get_db()
    if g.user["role"] in ("admin", "staff"):
        row = conn.execute(
            "SELECT id, title, messages FROM conversations WHERE id=?",
            (cid,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, title, messages FROM conversations WHERE id=? AND client_id=?",
            (cid, g.user["id"]),
        ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"id": row["id"], "title": row["title"], "messages": json.loads(row["messages"])})


@ai_bp.post("/generate")
@limiter.limit("20 per hour")
@require_role("client", "staff", "admin")
def generate():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    context = (data.get("context") or "").strip()

    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    if len(prompt) > 4000:
        return jsonify({"error": "prompt too long (max 4000 chars)"}), 400
    if len(context) > 4000:
        return jsonify({"error": "context too long (max 4000 chars)"}), 400

    try:
        output = claude_service.generate_content(prompt, context)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    conn = get_db()
    conn.execute(
        "INSERT INTO service_requests (client_id, type, prompt, status, output_text) VALUES (?,?,?,?,?)",
        (g.user["id"], "content", prompt, "completed", output),
    )
    conn.commit()
    return jsonify({"output": output})


@ai_bp.post("/chat")
@limiter.limit("30 per hour")
@require_role("client", "staff", "admin")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")

    if not message:
        return jsonify({"error": "message required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "message too long (max 2000 chars)"}), 400

    conn = get_db()
    history = []
    if conversation_id:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id=? AND client_id=?",
            (conversation_id, g.user["id"]),
        ).fetchone()
        if row:
            history = json.loads(row["messages"])

    history = history[-38:]  # cap before API call — leaves room for user+assistant

    try:
        reply = claude_service.chat(history, message)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})

    if conversation_id and conn.execute(
        "SELECT id FROM conversations WHERE id=? AND client_id=?", (conversation_id, g.user["id"])
    ).fetchone():
        conn.execute(
            "UPDATE conversations SET messages=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(history), conversation_id),
        )
    else:
        title = message[:60] + ("…" if len(message) > 60 else "")
        cur = conn.execute(
            "INSERT INTO conversations (client_id, title, messages) VALUES (?,?,?)",
            (g.user["id"], title, json.dumps(history)),
        )
        conversation_id = cur.lastrowid

    conn.commit()
    return jsonify({"reply": reply, "conversation_id": conversation_id})


@ai_bp.post("/process-file")
@limiter.limit("10 per hour")
@require_role("client", "staff", "admin")
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400

    file = request.files["file"]
    instruction = (request.form.get("instruction") or "Analyze and summarize this file.").strip()

    if not file_service.allowed(file.filename):
        return jsonify({"error": "File type not allowed"}), 400
    if len(instruction) > 2000:
        return jsonify({"error": "instruction too long (max 2000 chars)"}), 400

    try:
        file_info = file_service.save_upload(file, g.user["id"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    conn = get_db()
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
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
        try:
            os.remove(file_info["path"])
        except OSError:
            pass
        return jsonify({"error": str(e)}), 500

    conn.execute(
        "INSERT INTO service_requests (client_id, type, prompt, file_id, status, output_text) VALUES (?,?,?,?,?,?)",
        (g.user["id"], "file", instruction, file_id, "completed", output),
    )
    conn.commit()

    return jsonify({
        "output": output,
        "file": {
            "id": file_id,
            "original_name": file_info["original_name"],
            "file_type": file_info["file_type"],
            "size": file_info["size"],
        },
    })
