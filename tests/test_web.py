from unittest.mock import patch

from app.main import app


def test_public_page_uses_runtime_snapshot_when_database_fails(client):
    snapshot = {"profile": {"full_name": "Cached Candidate", "headline": "Analytics engineer", "summary": "A cached profile.", "email": "hello@example.com"}, "experience": [], "projects": [], "skill_categories": [], "education": [], "credentials": []}
    app.state.snapshot_store.save(snapshot)

    with patch("app.main.build_public_profile", side_effect=RuntimeError("database offline")):
        response = client.get("/")

    assert response.status_code == 200
    assert "Cached Candidate" in response.text
    assert "database offline" not in response.text


def test_admin_requires_authentication(client):
    assert client.get("/admin").status_code == 401
    assert client.get("/api/v1/admin/profile").status_code == 401


def test_admin_login_allows_authenticated_profile_read(client, admin_user):
    login = client.post("/api/v1/auth/login", data={"username": admin_user.username, "password": "correct horse battery staple"})

    assert login.status_code == 200
    response = client.get("/api/v1/admin/profile")
    assert response.status_code == 200
