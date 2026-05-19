import threading
import anthropic
from config import Config

_client = None
_client_lock = threading.Lock()


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_AGENCY = (
    "You are RigweAI Agency's AI assistant. You help clients with content creation, "
    "analysis, and business tasks. Be professional, concise, and helpful."
)


def generate_content(prompt: str, context: str = "") -> str:
    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nTask:\n{prompt}"})
    else:
        messages.append({"role": "user", "content": prompt})

    resp = _get_client().messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_AGENCY,
        messages=messages,
    )
    return resp.content[0].text


def chat(history: list[dict], new_message: str) -> str:
    messages = list(history)
    messages.append({"role": "user", "content": new_message})
    resp = _get_client().messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_AGENCY,
        messages=messages,
    )
    return resp.content[0].text


def analyze_file(file_text: str, instruction: str, image_b64: str = None, media_type: str = None) -> str:
    if image_b64:
        content = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": image_b64},
            },
            {"type": "text", "text": instruction or "Describe and analyze this image in detail."},
        ]
    else:
        content = f"File content:\n\n{file_text[:12000]}\n\nInstruction: {instruction}"

    resp = _get_client().messages.create(
        model=Config.CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_AGENCY,
        messages=[{"role": "user", "content": content}],
    )
    return resp.content[0].text
