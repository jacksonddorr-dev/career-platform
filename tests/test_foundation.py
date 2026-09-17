from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_health_endpoint_reports_service_status_without_configuration_secrets():
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "career-platform"}
    assert "secret" not in response.text.lower()


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_NAME", "Test Career Platform")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_env == "test"
    assert settings.app_name == "Test Career Platform"
    get_settings.cache_clear()
