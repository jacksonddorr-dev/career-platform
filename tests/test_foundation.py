import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings, normalize_database_url
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


@pytest.mark.parametrize("raw", ["postgresql://u:p@h:5432/db", "postgres://u:p@h:5432/db"])
def test_railway_postgres_urls_use_psycopg_driver(raw):
    assert normalize_database_url(raw) == "postgresql+psycopg://u:p@h:5432/db"


@pytest.mark.parametrize("url", ["sqlite:///./career_platform.db", "postgresql+psycopg://u:p@h/db"])
def test_other_urls_are_unchanged(url):
    assert normalize_database_url(url) == url


def test_settings_normalize_database_url_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/db")
    get_settings.cache_clear()
    try:
        assert get_settings().database_url == "postgresql+psycopg://u:p@h:5432/db"
    finally:
        get_settings.cache_clear()


def test_alembic_config_accepts_percent_in_password(monkeypatch):
    from alembic.config import Config
    from alembic.runtime.environment import EnvironmentContext
    from alembic.script import ScriptDirectory

    monkeypatch.setenv("DATABASE_URL", "sqlite:///./pct%25test.db")
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        script = ScriptDirectory.from_config(config)
        with EnvironmentContext(config, script, as_sql=True, fn=lambda rev, ctx: []):
            script.run_env()
        assert config.get_main_option("sqlalchemy.url") == "sqlite:///./pct%25test.db"
    finally:
        get_settings.cache_clear()


def test_railway_starts_via_script_that_migrates_and_binds_public_port():
    config = json.loads(Path("railway.json").read_text())
    assert config["deploy"]["startCommand"] == "sh scripts/start.sh"
    assert config["deploy"]["healthcheckPath"] == "/api/v1/health"
    script = Path("scripts/start.sh").read_text()
    assert "alembic upgrade head" in script
    assert '--host 0.0.0.0 --port "${PORT:-8000}"' in script
