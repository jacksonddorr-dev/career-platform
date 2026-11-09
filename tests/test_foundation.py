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


def test_start_script_writes_real_snapshot_after_migrating_without_blocking_boot():
    lines = Path("scripts/start.sh").read_text().splitlines()
    migrate = next(i for i, line in enumerate(lines) if "alembic upgrade head" in line)
    snapshot = next(i for i, line in enumerate(lines) if "python -m app.snapshot" in line)
    server = next(i for i, line in enumerate(lines) if "uvicorn" in line)
    assert migrate < snapshot < server
    # start.sh runs under `set -e`, so a failed snapshot must be caught or the app never starts.
    assert "||" in lines[snapshot]


def test_ec2_service_binds_loopback_and_migrates_before_start():
    unit = Path("deploy/career-platform.service").read_text()
    lines = unit.splitlines()
    assert "--host 127.0.0.1 --port 8000 --workers 2" in unit
    assert "0.0.0.0" not in unit and "forwarded-allow-ips" not in unit
    migrate = next(i for i, line in enumerate(lines) if line.startswith("ExecStartPre=") and "alembic upgrade head" in line)
    snapshot = next(i for i, line in enumerate(lines) if "app.snapshot" in line)
    start = next(i for i, line in enumerate(lines) if line.startswith("ExecStart="))
    assert migrate < snapshot < start
    # The leading "-" lets a failed snapshot continue; a failed migration must still stop the start.
    assert lines[snapshot].startswith("ExecStartPre=-")
    for setting in ("Restart=always", "User=ubuntu", "WorkingDirectory=/home/ubuntu/career-platform"):
        assert setting in lines


def test_ec2_nginx_redirects_http_and_forwards_proto():
    conf = Path("deploy/nginx-career-platform.conf").read_text()
    for directive in ("return 301 https://jacksoncareer.me$request_uri;", "listen 443 ssl;",
                      "proxy_pass http://127.0.0.1:8000;", "proxy_set_header X-Forwarded-Proto $scheme;"):
        assert directive in conf


def test_deploy_script_shows_logs_when_restart_fails():
    # A failed migration makes `systemctl restart` itself fail; under `set -e` that used to
    # exit before the logs were printed, hiding the reason.
    script = Path("deploy/deploy.sh").read_text()
    assert "if ! sudo systemctl restart career-platform; then" in script
    assert script.count("journalctl -u career-platform") == 1
