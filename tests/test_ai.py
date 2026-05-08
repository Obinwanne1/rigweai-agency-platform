import io
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from app import app

MOCK_RESPONSE = "This is a mock Claude response."


def _mock_content():
    m = MagicMock()
    m.content = [MagicMock(text=MOCK_RESPONSE)]
    return m


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _admin_token(client):
    r = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    return r.get_json()["token"]


# ── Generate ───────────────────────────────────────────────────────────

@patch("services.claude_service._get_client")
def test_generate_content(mock_client, client):
    mock_client.return_value.messages.create.return_value = _mock_content()
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate", json={"prompt": "Write a test post."},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    assert resp.get_json()["output"] == MOCK_RESPONSE


def test_generate_missing_prompt(client):
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate", json={},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400


def test_generate_unauthenticated(client):
    resp = client.post("/api/ai/generate", json={"prompt": "test"})
    assert resp.status_code == 401


def test_generate_prompt_too_long(client):
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate", json={"prompt": "x" * 4001},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400


def test_generate_context_too_long(client):
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate",
                       json={"prompt": "valid prompt", "context": "x" * 4001},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400


# ── Chat ───────────────────────────────────────────────────────────────

@patch("services.claude_service._get_client")
def test_chat(mock_client, client):
    mock_client.return_value.messages.create.return_value = _mock_content()
    tok = _admin_token(client)
    resp = client.post("/api/ai/chat", json={"message": "Hello"},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reply"] == MOCK_RESPONSE
    assert "conversation_id" in data


def test_chat_message_too_long(client):
    tok = _admin_token(client)
    resp = client.post("/api/ai/chat", json={"message": "x" * 2001},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400


# ── Process file ───────────────────────────────────────────────────────

@patch("services.claude_service._get_client")
def test_process_file_txt(mock_client, client):
    from config import Config
    mock_client.return_value.messages.create.return_value = _mock_content()
    tok = _admin_token(client)
    tmp_dir = tempfile.mkdtemp()
    orig_dir = Config.UPLOAD_DIR
    Config.UPLOAD_DIR = tmp_dir
    try:
        resp = client.post(
            "/api/ai/process-file",
            data={"file": (io.BytesIO(b"Hello world content"), "test.txt"),
                  "instruction": "Summarize this."},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["output"] == MOCK_RESPONSE
        assert data["file"]["file_type"] == "txt"
    finally:
        Config.UPLOAD_DIR = orig_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_process_file_invalid_type(client):
    tok = _admin_token(client)
    resp = client.post(
        "/api/ai/process-file",
        data={"file": (io.BytesIO(b"evil"), "malware.exe")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert resp.status_code == 400


def test_instruction_too_long(client):
    from config import Config
    tok = _admin_token(client)
    tmp_dir = tempfile.mkdtemp()
    orig_dir = Config.UPLOAD_DIR
    Config.UPLOAD_DIR = tmp_dir
    try:
        resp = client.post(
            "/api/ai/process-file",
            data={"file": (io.BytesIO(b"content"), "test.txt"),
                  "instruction": "x" * 2001},
            content_type="multipart/form-data",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 400
    finally:
        Config.UPLOAD_DIR = orig_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Conversation ownership ─────────────────────────────────────────────

@patch("services.claude_service._get_client")
def test_conversation_ownership(mock_client, client):
    """Client cannot read another user's conversation."""
    mock_client.return_value.messages.create.return_value = _mock_content()

    tok_admin = _admin_token(client)

    # Create client2
    client.post("/api/admin/users",
                json={"email": "client2@test.com", "name": "Client2",
                      "role": "client", "password": "Pass1234!"},
                headers={"Authorization": f"Bearer {tok_admin}"})
    tok2 = client.post("/api/auth/login",
                       json={"email": "client2@test.com", "password": "Pass1234!"}).get_json()["token"]

    # Admin creates a conversation
    r = client.post("/api/ai/chat", json={"message": "Hello"},
                    headers={"Authorization": f"Bearer {tok_admin}"})
    cid = r.get_json()["conversation_id"]

    # client2 (role=client) cannot read admin's conversation
    resp = client.get(f"/api/ai/conversations/{cid}",
                      headers={"Authorization": f"Bearer {tok2}"})
    assert resp.status_code == 404
