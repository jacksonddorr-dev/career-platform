from unittest.mock import patch

import pytest

from app.main import app
from app.models import Profile, Project, Status


def save_snapshot_with_project():
    app.state.snapshot_store.save({"profile": {"full_name": "Cached Candidate", "headline": "Analytics engineer", "summary": "A cached profile.", "email": "hello@example.com"}, "experience": [], "projects": [{"title": "Snapshot Project"}], "skill_categories": [], "education": [], "credentials": []})


def add_published_project(db_session):
    profile = Profile(full_name="Live Candidate", headline="Analytics engineer", status=Status.PUBLISHED)
    db_session.add(profile)
    db_session.flush()
    db_session.add(Project(profile_id=profile.id, title="Live Project", status=Status.PUBLISHED))
    db_session.commit()


@pytest.mark.parametrize("path", ["/", "/about", "/projects"])
def test_database_failure_keeps_profile_hides_projects_and_returns_503(client, path):
    save_snapshot_with_project()

    with patch("app.main.build_public_profile", side_effect=RuntimeError("database offline")):
        response = client.get(path)

    assert response.status_code == 503
    assert "Cached Candidate" in response.text
    assert "Projects temporarily unavailable" in response.text
    assert "Snapshot Project" not in response.text
    assert "database offline" not in response.text


def test_database_failure_without_snapshot_returns_503_with_no_placeholder(client):
    with patch("app.main.build_public_profile", side_effect=RuntimeError("database offline")):
        response = client.get("/")

    assert response.status_code == 503
    assert "Cached Candidate" not in response.text
    assert "example.com" not in response.text


def test_healthy_request_lists_projects_with_200(client, db_session):
    add_published_project(db_session)

    response = client.get("/")

    assert response.status_code == 200
    assert "Live Project" in response.text
    assert "Projects temporarily unavailable" not in response.text


def test_projects_return_after_database_recovers_without_restart(client, db_session):
    add_published_project(db_session)
    save_snapshot_with_project()

    with patch("app.main.build_public_profile", side_effect=RuntimeError("database offline")):
        failed = client.get("/")
    recovered = client.get("/")

    assert failed.status_code == 503
    assert recovered.status_code == 200
    assert "Live Project" in recovered.text


def test_admin_requires_authentication(client):
    assert client.get("/admin").status_code == 401
    assert client.get("/api/v1/admin/profile").status_code == 401


def test_admin_login_allows_authenticated_profile_read(client, admin_user):
    login = client.post("/api/v1/auth/login", data={"username": admin_user.username, "password": "correct horse battery staple"})

    assert login.status_code == 200
    response = client.get("/api/v1/admin/profile")
    assert response.status_code == 200


def test_privacy_page_is_linked_from_footer(client):
    snapshot = {"profile": {"full_name": "Cached Candidate", "headline": "Analytics engineer", "email": "hello@example.com"}, "experience": [], "projects": [], "skill_categories": [], "education": [], "credentials": []}
    app.state.snapshot_store.save(snapshot)

    with patch("app.main.build_public_profile", return_value=None):
        home = client.get("/")
        privacy = client.get("/privacy")

    assert '<a href="/privacy">Privacy</a>' in home.text
    assert privacy.status_code == 200
    assert "_ga_XWCRC21WXW" in privacy.text
    assert "mailto:hello@example.com" in privacy.text



def test_google_tag_waits_for_consent_on_each_public_page(client):
    snapshot = {"profile": {"full_name": "Cached Candidate", "headline": "Analytics engineer", "email": "hello@example.com"}, "experience": [], "projects": [], "skill_categories": [], "education": [], "credentials": []}
    app.state.snapshot_store.save(snapshot)

    with patch("app.main.build_public_profile", return_value=None):
        for path in ["/", "/about", "/experience", "/projects", "/skills", "/education", "/contact", "/privacy"]:
            html = client.get(path).text
            # gtag.js is injected by script only after consent, never as a static tag.
            assert '<script async src="https://www.googletagmanager.com' not in html, path
            assert html.count("https://www.googletagmanager.com/gtag/js?id=") == 1, path
            assert html.count("gtag('consent', 'default'") == 1, path
            assert html.index("gtag('consent', 'default'") < html.index("gtag('config'"), path
            assert 'id="consent"' in html and "data-consent-allow" in html and "data-consent-decline" in html, path
            assert "data-consent-open" in html, path
