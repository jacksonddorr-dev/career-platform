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
