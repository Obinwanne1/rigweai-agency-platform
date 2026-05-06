import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert data["user"]["role"] == "admin"


def test_login_wrong_password(client):
    resp = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_missing_fields(client):
    resp = client.post("/api/auth/login", json={"email": "admin@rigweai.com"})
    assert resp.status_code == 400


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_authenticated(client):
    login = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    token = login.get_json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["role"] == "admin"


def test_logout(client):
    resp = client.post("/api/auth/logout", json={})
    assert resp.status_code == 200
