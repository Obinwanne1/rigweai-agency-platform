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


# ── Lockout ────────────────────────────────────────────────────────────

def test_account_lockout(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "wrong"})
    resp = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "wrong"})
    assert resp.status_code == 429


# ── Forgot / reset password ────────────────────────────────────────────

def test_forgot_password_nonexistent_email_returns_sent(client):
    # Enumeration prevention — unknown email still returns "sent"
    resp = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "sent"


def test_reset_password_full_flow(client):
    import sqlite3
    from config import Config

    # Token is created even when SMTP is unconfigured
    client.post("/api/auth/forgot-password", json={"email": "admin@rigweai.com"})

    conn = sqlite3.connect(Config.DB_PATH)
    row = conn.execute(
        "SELECT token FROM password_reset_tokens WHERE used=0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row, "No reset token found in DB"
    token = row[0]

    resp = client.post("/api/auth/reset-password",
                       json={"token": token, "new_password": "NewPass1!"})
    assert resp.status_code == 200

    # New password works
    assert client.post("/api/auth/login",
                       json={"email": "admin@rigweai.com", "password": "NewPass1!"}).status_code == 200
    # Old password rejected
    assert client.post("/api/auth/login",
                       json={"email": "admin@rigweai.com", "password": "admin123"}).status_code == 401


def test_reset_password_invalid_token(client):
    resp = client.post("/api/auth/reset-password",
                       json={"token": "deadbeefdeadbeef", "new_password": "NewPass1!"})
    assert resp.status_code == 400


def test_reset_password_expired_token(client):
    import sqlite3, datetime
    from config import Config

    conn = sqlite3.connect(Config.DB_PATH)
    admin_id = conn.execute(
        "SELECT id FROM users WHERE email='admin@rigweai.com'"
    ).fetchone()[0]
    expired = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    ).isoformat()
    conn.execute(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?,?,?)",
        (admin_id, "expiredtokenxyz", expired),
    )
    conn.commit()
    conn.close()

    resp = client.post("/api/auth/reset-password",
                       json={"token": "expiredtokenxyz", "new_password": "NewPass1!"})
    assert resp.status_code == 400


def test_reset_password_token_cannot_be_reused(client):
    import sqlite3
    from config import Config

    client.post("/api/auth/forgot-password", json={"email": "admin@rigweai.com"})
    conn = sqlite3.connect(Config.DB_PATH)
    row = conn.execute(
        "SELECT token FROM password_reset_tokens WHERE used=0 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    token = row[0]

    client.post("/api/auth/reset-password",
                json={"token": token, "new_password": "NewPass1!"})
    # Second use must fail
    resp = client.post("/api/auth/reset-password",
                       json={"token": token, "new_password": "AnotherPass1!"})
    assert resp.status_code == 400


# ── Change password ────────────────────────────────────────────────────

def test_change_password(client):
    login = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    token = login.get_json()["token"]
    resp = client.post("/api/auth/change-password",
                       json={"current_password": "admin123", "new_password": "NewPass1!"},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": "admin@rigweai.com", "password": "NewPass1!"}).status_code == 200


def test_change_password_wrong_current(client):
    login = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    token = login.get_json()["token"]
    resp = client.post("/api/auth/change-password",
                       json={"current_password": "wrong", "new_password": "NewPass1!"},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
