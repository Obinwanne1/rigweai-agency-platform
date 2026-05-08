"""Tests for multi-member projects and status updates."""
import json
import os
import sys
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config as cfg


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(cfg.Config, "DB_PATH", db_path)
    schema = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "schema.sql")
    conn = sqlite3.connect(db_path)
    with open(schema, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
    return db_path


@pytest.fixture
def app(tmp_db):
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, email, password):
    r = client.post("/api/auth/login",
                    json={"email": email, "password": password})
    return r


def _make_users(tmp_db):
    from services.auth_service import hash_password
    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                 ("admin@test.com", hash_password("pass"), "Admin", "admin"))
    conn.execute("INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                 ("staff1@test.com", hash_password("pass"), "Staff1", "staff"))
    conn.execute("INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                 ("staff2@test.com", hash_password("pass"), "Staff2", "staff"))
    conn.execute("INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                 ("client1@test.com", hash_password("pass"), "Client1", "client"))
    conn.execute("INSERT INTO users (email,password_hash,name,role) VALUES (?,?,?,?)",
                 ("client2@test.com", hash_password("pass"), "Client2", "client"))
    conn.commit()
    rows = {r[1]: r[0] for r in conn.execute("SELECT id,email FROM users").fetchall()}
    conn.close()
    return rows


# ── Project creation with multiple members ─────────────────────────────

def test_create_project_with_members(client, tmp_db):
    ids = _make_users(tmp_db)
    _login(client, "admin@test.com", "pass")

    r = client.post("/api/admin/projects", json={
        "title": "Multi Project",
        "client_id": ids["client1@test.com"],
        "member_ids": [
            {"user_id": ids["staff1@test.com"], "role": "staff"},
            {"user_id": ids["staff2@test.com"], "role": "staff"},
            {"user_id": ids["client2@test.com"], "role": "client"},
        ]
    })
    assert r.status_code == 201
    pid = r.get_json()["id"]

    conn = sqlite3.connect(tmp_db)
    members = conn.execute(
        "SELECT user_id, role FROM project_members WHERE project_id=?", (pid,)
    ).fetchall()
    conn.close()
    member_ids = {m[0] for m in members}
    assert ids["client1@test.com"] in member_ids   # auto-added primary client
    assert ids["staff1@test.com"] in member_ids
    assert ids["staff2@test.com"] in member_ids
    assert ids["client2@test.com"] in member_ids
    assert len(members) == 4


def test_add_remove_member(client, tmp_db):
    ids = _make_users(tmp_db)
    _login(client, "admin@test.com", "pass")

    r = client.post("/api/admin/projects", json={
        "title": "P", "client_id": ids["client1@test.com"]
    })
    pid = r.get_json()["id"]

    # Add staff member
    r = client.post(f"/api/admin/projects/{pid}/members",
                    json={"user_id": ids["staff1@test.com"], "role": "staff"})
    assert r.status_code == 201

    # Remove staff member
    r = client.delete(f"/api/admin/projects/{pid}/members/{ids['staff1@test.com']}")
    assert r.status_code == 200

    conn = sqlite3.connect(tmp_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM project_members WHERE project_id=? AND user_id=?",
        (pid, ids["staff1@test.com"])
    ).fetchone()[0]
    conn.close()
    assert count == 0


# ── Status updates ─────────────────────────────────────────────────────

def test_staff_can_update_project_status(client, tmp_db):
    ids = _make_users(tmp_db)

    # Create project and assign staff1
    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "P"))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO project_members (project_id,user_id,role) VALUES (?,?,?)",
                 (pid, ids["staff1@test.com"], "staff"))
    conn.commit()
    conn.close()

    _login(client, "staff1@test.com", "pass")
    r = client.patch(f"/api/staff/projects/{pid}/status",
                     json={"status": "work_in_progress"})
    assert r.status_code == 200

    conn = sqlite3.connect(tmp_db)
    status = conn.execute("SELECT status FROM projects WHERE id=?", (pid,)).fetchone()[0]
    conn.close()
    assert status == "work_in_progress"


def test_staff_cannot_update_unassigned_project(client, tmp_db):
    ids = _make_users(tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "P"))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    _login(client, "staff1@test.com", "pass")
    r = client.patch(f"/api/staff/projects/{pid}/status",
                     json={"status": "assigned"})
    assert r.status_code == 403


def test_client_can_update_project_status(client, tmp_db):
    ids = _make_users(tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "P"))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO project_members (project_id,user_id,role) VALUES (?,?,?)",
                 (pid, ids["client1@test.com"], "client"))
    conn.commit()
    conn.close()

    _login(client, "client1@test.com", "pass")
    r = client.patch(f"/api/client/projects/{pid}/status",
                     json={"status": "completed"})
    assert r.status_code == 200


def test_invalid_status_rejected(client, tmp_db):
    ids = _make_users(tmp_db)
    _login(client, "admin@test.com", "pass")

    conn = sqlite3.connect(tmp_db)
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "P"))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    r = client.patch(f"/api/staff/projects/{pid}/status",
                     json={"status": "flying"})
    assert r.status_code == 400


# ── Staff sees only assigned projects ──────────────────────────────────

def test_staff_only_sees_own_projects(client, tmp_db):
    ids = _make_users(tmp_db)

    conn = sqlite3.connect(tmp_db)
    # Project assigned to staff1
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "Staff1 Project"))
    pid1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO project_members (project_id,user_id,role) VALUES (?,?,?)",
                 (pid1, ids["staff1@test.com"], "staff"))
    # Project NOT assigned to staff1
    conn.execute("INSERT INTO projects (client_id,title) VALUES (?,?)",
                 (ids["client1@test.com"], "Other Project"))
    conn.commit()
    conn.close()

    _login(client, "staff1@test.com", "pass")
    r = client.get("/api/staff/projects")
    projects = r.get_json()
    assert len(projects) == 1
    assert projects[0]["title"] == "Staff1 Project"


# ── Staff permission bypass fix ────────────────────────────────────────

def test_staff_cannot_update_request_without_project(client, tmp_db):
    """Staff must not update service_requests with no project_id (bypass fix)."""
    ids = _make_users(tmp_db)

    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO service_requests (client_id, type, prompt) VALUES (?,?,?)",
        (ids["client1@test.com"], "content", "Do something"),
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    r = _login(client, "staff1@test.com", "pass")
    tok = r.get_json()["token"]
    resp = client.patch(f"/api/staff/requests/{rid}",
                        json={"status": "completed"},
                        headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 403
