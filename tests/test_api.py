import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _admin_token(client):
    r = client.post("/api/auth/login", json={"email": "admin@rigweai.com", "password": "admin123"})
    return r.get_json()["token"]


def test_admin_can_create_user(client):
    tok = _admin_token(client)
    resp = client.post("/api/admin/users", json={
        "email": "newclient@test.com", "name": "Test Client", "role": "client", "password": "pass1234"
    }, headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 201


def test_admin_can_list_users(client):
    tok = _admin_token(client)
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_cannot_create_user_without_auth(client):
    resp = client.post("/api/admin/users", json={
        "email": "x@x.com", "name": "X", "role": "client", "password": "pass1234"
    })
    assert resp.status_code == 401


def test_role_enforcement_client_vs_admin(client):
    tok = _admin_token(client)
    client.post("/api/admin/users", json={
        "email": "client@test.com", "name": "Client", "role": "client", "password": "pass1234"
    }, headers={"Authorization": f"Bearer {tok}"})
    r = client.post("/api/auth/login", json={"email": "client@test.com", "password": "pass1234"})
    client_tok = r.get_json()["token"]
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {client_tok}"})
    assert resp.status_code == 403


def test_create_project(client):
    tok = _admin_token(client)
    client.post("/api/admin/users", json={
        "email": "c2@test.com", "name": "Client2", "role": "client", "password": "pass1234"
    }, headers={"Authorization": f"Bearer {tok}"})
    users = client.get("/api/admin/users", headers={"Authorization": f"Bearer {tok}"}).get_json()
    client_id = next(u["id"] for u in users if u["email"] == "c2@test.com")
    resp = client.post("/api/admin/projects", json={
        "title": "Test Project", "client_id": client_id
    }, headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 201


def test_stats_endpoint(client):
    tok = _admin_token(client)
    resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "users" in data and "projects" in data


# ── Health check ───────────────────────────────────────────────────────

def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["db"] is True


# ── Security headers ───────────────────────────────────────────────────

def test_security_headers_present(client):
    resp = client.get("/login")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in resp.headers
    assert "Referrer-Policy" in resp.headers


def test_csp_blocks_external_scripts(client):
    csp = client.get("/login").headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
