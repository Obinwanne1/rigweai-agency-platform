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


@patch("services.claude_service._get_client")
def test_generate_content(mock_client, client):
    mock_client.return_value.messages.create.return_value = _mock_content()
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate", json={"prompt": "Write a test post."},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    assert resp.get_json()["output"] == MOCK_RESPONSE


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


def test_generate_missing_prompt(client):
    tok = _admin_token(client)
    resp = client.post("/api/ai/generate", json={},
                       headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 400


def test_generate_unauthenticated(client):
    resp = client.post("/api/ai/generate", json={"prompt": "test"})
    assert resp.status_code == 401
