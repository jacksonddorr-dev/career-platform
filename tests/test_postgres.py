import io
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings, normalize_database_url

TEST_URL = os.environ.get("TEST_DATABASE_URL")
needs_postgres = pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL not set")


def _alembic(monkeypatch, url, buffer=None):
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    return Config("alembic.ini", output_buffer=buffer)


def _offline_postgres_sql(monkeypatch, run):
    buffer = io.StringIO()
    try:
        run(_alembic(monkeypatch, "postgresql://u:p@h/db", buffer))
    finally:
        get_settings.cache_clear()
    return buffer.getvalue()


def test_postgres_upgrade_creates_status_type_once(monkeypatch):
    sql = _offline_postgres_sql(monkeypatch, lambda config: command.upgrade(config, "head", sql=True))
    assert sql.count("CREATE TYPE status") == 1


def test_postgres_downgrade_drops_status_type(monkeypatch):
    sql = _offline_postgres_sql(monkeypatch, lambda config: command.downgrade(config, "0001_initial:base", sql=True))
    assert "DROP TYPE IF EXISTS status" in sql
    assert sql.index("DROP TABLE profiles") < sql.index("DROP TYPE IF EXISTS status")


@pytest.fixture
def pg_url(monkeypatch):
    url = normalize_database_url(TEST_URL)
    engine = create_engine(url)
    with engine.connect() as conn:
        for table in inspect(conn).get_table_names():
            if table != "alembic_version" and conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar():
                pytest.fail(f"{table} has rows; refusing to run destructive Postgres tests")
    config = _alembic(monkeypatch, url)
    command.downgrade(config, "base")
    yield url
    command.downgrade(_alembic(monkeypatch, url), "base")
    get_settings.cache_clear()
    engine.dispose()


@needs_postgres
def test_migration_round_trips_on_postgres(pg_url, monkeypatch):
    config = _alembic(monkeypatch, pg_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    with create_engine(pg_url).connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pg_type WHERE typname = 'status'")).scalar() == 0
    command.upgrade(config, "head")


@needs_postgres
def test_copy_into_postgres_resets_id_sequences(pg_url, monkeypatch, tmp_path):
    from sqlalchemy.orm import Session

    from app.copy_db import copy_database
    from app.models import Profile, Status
    from test_copy_db import make_source

    command.upgrade(_alembic(monkeypatch, pg_url), "head")
    copy_database(make_source(tmp_path / "src.db"), pg_url)

    with Session(create_engine(pg_url)) as db:
        new = Profile(full_name="Next", headline="x", status=Status.DRAFT)
        db.add(new)
        db.commit()
        assert new.id == 8
        db.delete(new)
        db.commit()
