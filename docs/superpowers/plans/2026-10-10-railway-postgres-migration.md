# Railway + PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tick each step and add a **Result** line as you go.

> **Redacted for publishing:** the Railway Postgres public URL (with its password) is `<RAILWAY_PUBLIC_DB_URL>` and the Railway-generated domain is `<RAILWAY_DOMAIN>`. The real values live in Railway and in the gitignored `.env`.

**Goal:** Serve jacksoncareer.me from the existing Railway `web` service, backed by the existing Railway Postgres, carrying over all content currently in the VM's SQLite database. Keep the Azure VM untouched as a rollback.

**Architecture:** The app code barely changes. A Postgres driver is added, Railway's `postgresql://` URL is normalized for SQLAlchemy, and the Alembic downgrade is made Postgres-safe. Railway builds from GitHub `main` with Railpack (uv). A start script runs `alembic upgrade head` and then uvicorn on `$PORT`. A one-shot `app.copy_db` script copies the VM's SQLite rows into Postgres, keeping their ids, and resets the id sequences. DNS for jacksoncareer.me then moves from the VM (52.159.85.45) to Railway.

**Tech Stack:** FastAPI, SQLAlchemy 2.1, Alembic 1.20, psycopg 3, uv, Railway (Railpack builder, managed Postgres).

**Spec:** No separate spec doc. This plan comes from the 2026-10-10 inspection recorded under *Starting state* below.

## Starting state (inspected 2026-10-10)

| Thing | Fact |
|---|---|
| Running code | VM at `94463c0`, systemd `career-platform`, uvicorn `127.0.0.1:8000 --workers 2`, behind nginx + Let's Encrypt for `jacksoncareer.me` and `www`. Both names resolve to `52.159.85.45`. |
| VM Python | 3.12.3 |
| VM data (`career_platform.db`) | profiles 1, experiences 3, achievements 10, skill_categories 3, skills 21, education 1, admin_users 1, credentials/projects/project_highlights 0. `alembic_version` = `0001_initial`. Status values are stored as names (`PUBLISHED`). |
| DB code | `app/db.py:make_engine` uses `get_settings().database_url`. No Postgres driver in `pyproject.toml`. `alembic/env.py` takes its URL from settings. |
| Enum | `models.py` uses `Enum(Status)` and the migration uses `sa.Enum(..., name="status")`. On Postgres this becomes a named type that `downgrade()` never drops. |
| Snapshot | `app/snapshot.py` writes `data/public-profile.json` on each good render. It's tracked in git, so a fresh Railway container starts with the committed copy, which is acceptable as a fallback. |
| Secret hygiene | The working tree's `.env.example` has an **uncommitted** line containing the real Railway Postgres URL. It isn't in git history or on GitHub. Task 0 moves it out. |
| Local tools | No `docker`, `psql`, or `railway` CLI. Railway steps are done by Jackson in the dashboard. |

## Global Constraints

- Python `>=3.11` (pyproject). Pin Railway to `3.12` to match the VM.
- No secret in any committed file: DB URLs with passwords, `SESSION_SECRET`, `ADMIN_PASSWORD`.
- The Railway web service reads the DB via the reference variable `${{Postgres.DATABASE_URL}}` (private network), never the public proxy URL.
- The public proxy URL `<RAILWAY_PUBLIC_DB_URL>` is used only from the laptop, only for Task 2's rehearsal and Task 5's copy, read from `.env` as `RAILWAY_DATABASE_URL`.
- The VM isn't modified by this plan. It stays the rollback until a separate decommission plan.
- Existing tests keep using in-memory SQLite. Postgres tests run only when `TEST_DATABASE_URL` is set.

## Review Focus

1. **Railway's raw `postgresql://` URL** reaches `create_engine` and boot fails looking for psycopg2. Expected: it's normalized to `postgresql+psycopg://`. Test in Task 1.
2. **A DB password containing `%`** breaks Alembic's configparser interpolation. Expected: migrations still run. Test in Task 1.
3. **Rows copied with explicit ids but sequences not reset**, so the first admin create after cutover fails with a duplicate key. Expected: the next insert gets `max(id)+1`. Test in Task 3 (Postgres).
4. **The copy is run twice, or into a non-empty DB.** Expected: it refuses and writes nothing. Test in Task 3.
5. **`downgrade` leaves the `status` enum type behind**, so a later `upgrade` fails with "type already exists". Expected: upgrade → downgrade → upgrade is clean. Test in Task 2.

---

### Task 0: Move the Railway DB URL out of `.env.example` [laptop, no commit]

**Result (2026-10-10):** The URL is now in `.env` as `RAILWAY_DATABASE_URL=...` (gitignored), and `.env.example` matches HEAD. Rotating the password is still Jackson's call (Step 2 was not done).

- [x] **Step 1:** Append the URL to the gitignored `.env` in valid syntax, then restore `.env.example` to HEAD.

```bash
grep -q '^RAILWAY_DATABASE_URL=' .env || \
  sed -n 's/^RAILWAY_DATABASE_URL: */RAILWAY_DATABASE_URL=/p' .env.example >> .env
git checkout -- .env.example
git check-ignore .env && git diff --stat -- .env.example   # .env ignored, no diff
```

- [x] **Step 2 (Jackson decides):** Optionally rotate the Postgres password in Railway. It has never been committed, but it has been in plaintext in a tracked file's working copy.

### Task 1: Postgres driver + URL normalization

**Result (2026-10-10):** Commit `f5fa2d1`. psycopg 3.3.6 added. I confirmed the `%` test fails without the `env.py` escape. 17 passed.

**Files:**
- Modify: `pyproject.toml` (dependencies), `uv.lock`
- Modify: `app/config.py`
- Modify: `alembic/env.py:7`
- Test: `tests/test_foundation.py`

**Interfaces:**
- Produces: `app.config.normalize_database_url(url: str) -> str`. `Settings.database_url` is always normalized.

- [x] **Step 1: Write the failing tests** (append to `tests/test_foundation.py`)

```python
import pytest

from app.config import normalize_database_url


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
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext

    monkeypatch.setenv("DATABASE_URL", "sqlite:///./pct%25test.db")
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        with EnvironmentContext(config, ScriptDirectory.from_config(config), as_sql=True,
                                fn=lambda rev, ctx: []):
            ScriptDirectory.from_config(config).run_env()
        assert config.get_main_option("sqlalchemy.url") == "sqlite:///./pct%25test.db"
    finally:
        get_settings.cache_clear()
```

- [x] **Step 2: Run the tests to confirm they fail**

Run: `uv run pytest tests/test_foundation.py -v`
Expected: FAIL with `ImportError: cannot import name 'normalize_database_url'`.

- [x] **Step 3: Implement**

`app/config.py`: add the function and a validator.

```python
from pydantic import field_validator
...
def normalize_database_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    ...
    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)
```

`alembic/env.py` line 7:

```python
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
```

Add the driver: `uv add "psycopg[binary]>=3.2,<4"`. This updates `pyproject.toml` and `uv.lock`.

- [x] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass. Then `git checkout -- data/public-profile.json`, because pytest overwrites it (a known issue).

- [x] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock app/config.py alembic/env.py tests/test_foundation.py
git commit -m "Add psycopg and normalize Postgres URLs for Railway"
```

### Task 2: Make the migration round-trip on Postgres

**Result (2026-10-10):** Commit `0ca8844`. The live Postgres tests were skipped at Jackson's choice. In their place, offline `--sql` tests rendered the Postgres DDL. They showed that upgrade creates `status` exactly once and that downgrade was missing `DROP TYPE`; the second test failed first and passed after the fix. The downgrade uses `op.execute("DROP TYPE IF EXISTS status")` behind a dialect check, instead of `Enum.drop(checkfirst=True)`, which needs a live connection. 19 passed, 1 skipped.

**Files:**
- Modify: `alembic/versions/0001_initial.py` (`downgrade`)
- Create: `tests/test_postgres.py`

**Interfaces:**
- Consumes: `normalize_database_url` (Task 1).
- Produces: a `pg_url` fixture in `tests/test_postgres.py`. It skips without `TEST_DATABASE_URL`, refuses to touch a DB that has rows, and leaves the DB at `base` (empty) afterwards.

- [x] **Step 1: Write the failing test**

```python
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings, normalize_database_url

TEST_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL not set")


def _alembic(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    return Config("alembic.ini")


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


def test_migration_round_trips_on_postgres(pg_url, monkeypatch):
    config = _alembic(monkeypatch, pg_url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    with create_engine(pg_url).connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pg_type WHERE typname = 'status'")).scalar() == 0
    command.upgrade(config, "head")
```

- [x] **Step 2: Run it against the empty Railway Postgres to confirm it fails**

Run: `TEST_DATABASE_URL="$(grep '^RAILWAY_DATABASE_URL=' .env | cut -d= -f2-)" uv run pytest tests/test_postgres.py -v`

> **Executed 2026-10-10:** Jackson declined running these against the Railway DB, so the live tests are skipped. `TEST_DATABASE_URL` must only ever point at a **scratch** database. The fixture now refuses any database that has been migrated (`alembic_version` set) or has rows, so it can't downgrade production after the first deploy.
Expected: FAIL. Either the `status` type count is 1, or the second upgrade errors with `type "status" already exists`. If the **first** upgrade fails with "already exists", record that too: the per-table enum creation needs `create_type=False` plus one explicit `status.create(op.get_bind(), checkfirst=True)` at the top of `upgrade()`.

- [x] **Step 3: Implement** (end of `downgrade()`)

```python
    sa.Enum(name="status").drop(op.get_bind(), checkfirst=True)
```

On SQLite this is a no-op.

- [x] **Step 4: Rerun Step 2's command, then `uv run pytest -q`**
Expected: PASS, and the full suite passes (with Postgres tests skipped when the env var isn't set). The Railway DB is left empty at `base`.

- [x] **Step 5: Commit**

```bash
git add alembic/versions/0001_initial.py tests/test_postgres.py
git commit -m "Drop the status enum on downgrade so migrations round-trip on Postgres"
```

### Task 3: SQLite → Postgres copy script

**Result (2026-10-10):** Commit `e4907ee`. There is no `tests/__init__.py`; the Postgres test imports `from test_copy_db import make_source`. A rehearsal copying the laptop DB into a scratch SQLite file gave 1/1/0/1/3/0/3/10/0/21 rows, matching the VM. The sequence reset hasn't been run on live Postgres; see Task 5 Step 5b. 21 passed, 2 skipped.

**Files:**
- Create: `app/copy_db.py`
- Test: `tests/test_copy_db.py`, plus one more test in `tests/test_postgres.py`

**Interfaces:**
- Consumes: `normalize_database_url`, `Base.metadata` (`app/models.py`), the `pg_url` fixture.
- Produces: `copy_database(source_url: str, target_url: str) -> dict[str, int]` (rows copied per table). Raises `ValueError` if any target table has rows. CLI: `python -m app.copy_db SOURCE_URL TARGET_URL`.

- [x] **Step 1: Write the failing tests** (`tests/test_copy_db.py`)

```python
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.copy_db import copy_database
from app.models import Base, Experience, Profile, Status


def make_source(path):
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        profile = Profile(id=7, full_name="Jackson", headline="Analyst", status=Status.PUBLISHED)
        db.add(profile)
        db.flush()
        db.add(Experience(id=42, profile_id=7, company_name="Acme", title="Intern", is_current=True,
                          start_date=date(2025, 6, 1), status=Status.PUBLISHED))
        db.commit()
    engine.dispose()
    return url


def make_target(path):
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


def test_copy_preserves_ids_enums_dates_and_booleans(tmp_path):
    source, target = make_source(tmp_path / "src.db"), make_target(tmp_path / "dst.db")

    counts = copy_database(source, target)

    assert counts["profiles"] == 1 and counts["experiences"] == 1 and counts["skills"] == 0
    with Session(create_engine(target)) as db:
        exp = db.scalars(select(Experience)).one()
        assert (exp.id, exp.profile_id, exp.is_current, exp.start_date, exp.status) == \
               (42, 7, True, date(2025, 6, 1), Status.PUBLISHED)


def test_copy_refuses_non_empty_target_and_writes_nothing(tmp_path):
    source, target = make_source(tmp_path / "src.db"), make_target(tmp_path / "dst.db")
    copy_database(source, target)

    with pytest.raises(ValueError, match="not empty"):
        copy_database(source, target)

    with Session(create_engine(target)) as db:
        assert len(db.scalars(select(Profile)).all()) == 1
```

Append to `tests/test_postgres.py`:

```python
def test_copy_into_postgres_resets_id_sequences(pg_url, monkeypatch, tmp_path):
    from sqlalchemy.orm import Session
    from app.copy_db import copy_database
    from app.models import Profile, Status
    from tests.test_copy_db import make_source

    command.upgrade(_alembic(monkeypatch, pg_url), "head")
    copy_database(make_source(tmp_path / "src.db"), pg_url)

    with Session(create_engine(pg_url)) as db:
        new = Profile(full_name="Next", headline="x", status=Status.DRAFT)
        db.add(new)
        db.commit()
        assert new.id == 8
        db.delete(new)
        db.commit()
```

(For `from tests.test_copy_db import ...` to work, `tests/` needs an `__init__.py`. If it doesn't have one, create an empty one in this step.)

- [x] **Step 2: Run to confirm failure**

Run: `uv run pytest tests/test_copy_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.copy_db'`.

- [x] **Step 3: Implement** `app/copy_db.py`

```python
"""Copy every app row from one database into an empty, migrated one (VM SQLite -> Railway Postgres)."""
import sys

from sqlalchemy import create_engine, func, select, text

from app.config import normalize_database_url
from app.models import Base


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source = create_engine(normalize_database_url(source_url))
    target = create_engine(normalize_database_url(target_url))
    tables = Base.metadata.sorted_tables
    counts: dict[str, int] = {}
    try:
        with source.connect() as src, target.begin() as dst:
            for table in tables:
                if dst.execute(select(func.count()).select_from(table)).scalar_one():
                    raise ValueError(f"target table {table.name} is not empty; refusing to copy")
            for table in tables:
                rows = [dict(row._mapping) for row in src.execute(select(table))]
                if rows:
                    dst.execute(table.insert(), rows)
                counts[table.name] = len(rows)
            if target.dialect.name == "postgresql":
                for table in tables:
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"))
    finally:
        source.dispose()
        target.dispose()
    return counts


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m app.copy_db SOURCE_URL TARGET_URL")
    for name, count in copy_database(sys.argv[1], sys.argv[2]).items():
        print(f"{name}: {count}")
```

- [x] **Step 4: Run**
`uv run pytest -q` → PASS. Then rerun Task 2 Step 2's command → all Postgres tests PASS, and the DB is left empty.

- [x] **Step 5: Commit**

```bash
git add app/copy_db.py tests/test_copy_db.py tests/test_postgres.py tests/__init__.py
git commit -m "Add one-shot SQLite to Postgres copy that keeps ids and resets sequences"
```

### Task 4: Railway build/start config + README

**Result (2026-10-10):** Commit `6c4ce35`, on branch `worktree-railway-migration` and **not pushed**: merging and pushing to `main` is Jackson's call. A local smoke boot of `scripts/start.sh` (scratch SQLite, PORT=8765) returned health `ok` and migrated to `0001_initial`. With `.python-version` set, uv rebuilds the venv on 3.12, so run `uv sync --extra test` before `uv run pytest`. 22 passed, 2 skipped. The final review then added commit `e2fe8f4`: the guard refuses a migrated DB, and the plan gained Step 5b.

**Files:**
- Create: `railway.json`, `scripts/start.sh`, `.python-version`
- Modify: `README.md` (Deployment section)
- Test: `tests/test_foundation.py`

- [x] **Step 1: Write the failing test**

```python
import json
from pathlib import Path


def test_railway_starts_via_script_that_migrates_and_binds_public_port():
    config = json.loads(Path("railway.json").read_text())
    assert config["deploy"]["startCommand"] == "sh scripts/start.sh"
    assert config["deploy"]["healthcheckPath"] == "/api/v1/health"
    script = Path("scripts/start.sh").read_text()
    assert "alembic upgrade head" in script
    assert '--host 0.0.0.0 --port "${PORT:-8000}"' in script
```

- [x] **Step 2: Run** `uv run pytest tests/test_foundation.py -v` → FAIL (`FileNotFoundError`).

- [x] **Step 3: Implement**

`railway.json`:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": { "builder": "RAILPACK" },
  "deploy": {
    "startCommand": "sh scripts/start.sh",
    "healthcheckPath": "/api/v1/health",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

`scripts/start.sh`:

```sh
#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 \
  --proxy-headers --forwarded-allow-ips '*'
```

`.python-version`: `3.12`

`README.md`: replace the first paragraph of "Deployment and recovery". The new text says production runs on Railway, built from `main` per `railway.json`. `scripts/start.sh` migrates on every boot. `DATABASE_URL` is `${{Postgres.DATABASE_URL}}`. Rollback to the VM is described in `docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`.

- [x] **Step 4: Run** `uv run pytest -q` → PASS, then restore `data/public-profile.json`.

- [x] **Step 5: Commit and push** (pushing `main` is what Railway deploys from, once Task 5 connects it)

```bash
git add railway.json scripts/start.sh .python-version README.md tests/test_foundation.py
git commit -m "Add Railway build and start config"
git push origin main
```

### Task 5: Configure Railway, deploy, copy the data [Jackson in dashboard + laptop]

- [x] **Step 1 [Jackson]: Set the `web` service variables** *(the service is named `career-platform`)*
  - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
  - `SESSION_SECRET` = a new value from `python -c "import secrets; print(secrets.token_urlsafe(48))"`
  - `ADMIN_USERNAME` = same as the VM
  - `ADMIN_PASSWORD` = any strong value. It's only used by `app.seed`, which isn't run, because the admin user and hash are copied over.
  - `APP_ENV=production`
  - `SITE_URL=https://jacksoncareer.me`
  - **Annotation (2026-10-26, written afterward): only partly done until 2026-10-26.** A name-only listing (`railway variables -s career-platform --kv`, values not read) showed that `DATABASE_URL` was the only app variable set. Without `SESSION_SECRET` the app used the public default `change-me-in-production` from `app/config.py`, so anyone reading the repo could have signed an admin session cookie. Without `SITE_URL`, every page's `canonical` link pointed to `http://127.0.0.1:8000`. I don't know whether anyone used the default secret; the app keeps no record of admin logins.
  - **Fix (2026-10-26, ~01:57 UTC):** I set `SITE_URL=https://jacksoncareer.me`, `APP_ENV=production`, and a new 64-character `SESSION_SECRET` piped in through `--stdin`, so the value was never printed. Deployment `6c1e4147` came up SUCCESS with `Wrote data/public-profile.json`. Checks: `/`, `/about`, `/projects`, `/api/v1/health` → 200; `/about` canonical → `https://jacksoncareer.me/about`; a cookie signed with the old default for the username `admin` → 401 on `/admin`. `ADMIN_USERNAME` and `ADMIN_PASSWORD` stay unset on purpose: only `app.seed` reads them, and it isn't run.
- [x] **Step 2 [Jackson]:** Settings → Source: connect `jacksonddorr-dev/career-platform`, branch `main`. Then Networking → Generate Domain (`<RAILWAY_DOMAIN>`).
  - **Annotation (2026-10-26, written afterward):** Done, but the date isn't recorded. Every deployment Railway still lists (the oldest is 2026-10-19) shows repo `jacksonddorr-dev/career-platform`, branch `main`, and reason `deploy` for pushes. `railway domain list` shows the generated domain `career-platform-production-1a1e.up.railway.app` and the custom domain `jacksoncareer.me`, both on port 8080. Railway only lists the last 20 deployments, so the first connection and the first deploy are no longer visible.
- [x] **Step 3: Verify the first deploy** (laptop) *(partly; see annotation)*
  - `curl -s https://<RAILWAY_DOMAIN>/api/v1/health` returns `{"status":"ok",...}`
  - Alembic logs nothing (`alembic.ini` has no logging section), so confirm the migration from the laptop instead: `uv run python -c "import os; from sqlalchemy import create_engine, text; print(create_engine(os.environ['U'].replace('postgresql://','postgresql+psycopg://',1)).connect().execute(text('select version_num from alembic_version')).all())"` with `U` set to the `RAILWAY_DATABASE_URL` from `.env`. Expect `[('0001_initial',)]`.
  - `/` returns 200 and is served from the committed snapshot, since the DB is still empty.
  - **Found (2026-10-11 ~00:45 UTC, read-only check):** Railway Postgres was already at `0001_initial`, with all 10 tables empty. Nothing in this session migrated it. Either the `web` service is already connected and the push of `7cd922f` deployed it, or it was migrated by hand. Not yet confirmed in the Railway dashboard.
  - **Annotation (2026-10-26, written afterward):** Only the migration check was recorded, in the *Found* line above: Postgres was at `0001_initial` with empty tables before the copy. The health and `/` checks on the generated domain weren't recorded at the time, and the first deploy's logs are no longer listed. The same checks pass on the current deployment (see the 2026-10-26 checks in Step 1).
- [x] **Step 4: Freeze edits and pull the VM DB.** Make no admin edits until Task 6 is done. Use SQLite's online backup rather than `scp` of the live file:
  - **Result (2026-10-11):** I made an online backup on the VM at `~/backups/career_platform-20261011T002635Z.db` (sha256 `1520f2f1…0177d49e`, integrity `ok`, counts equal to live). It was copied to the laptop with a matching hash. For the comparison, I also pulled a fresh online snapshot of the live DB; the temp file on the VM was removed.

```bash
S=/private/tmp/claude-501/-Users-jacksondorr-career-platform/<session>/scratchpad
ssh -i ~/.ssh/isba4775_azure azureuser@52.159.85.45 \
  'cd ~/career-platform && .venv/bin/python -c "import sqlite3; s=sqlite3.connect(\"career_platform.db\"); d=sqlite3.connect(\"/tmp/cp-export.db\"); s.backup(d)"'
scp -i ~/.ssh/isba4775_azure azureuser@52.159.85.45:/tmp/cp-export.db "$S/cp-export.db"
```

- [x] **Step 5: Copy** (laptop)

```bash
uv run python -m app.copy_db "sqlite:///$S/cp-export.db" "$(grep '^RAILWAY_DATABASE_URL=' .env | cut -d= -f2-)"
```

Expected: profiles 1, experiences 3, achievements 10, skill_categories 3, skills 21, education 1, admin_users 1, others 0. These must match *Starting state*. If anything else changed, re-count on the VM first.

**Result (2026-10-11):** Copied from the backup. The copy printed exactly the expected counts. Then each table was compared row by row and column by column, after SQLAlchemy type conversion: VM live, the backup and Railway are **identical in all 10 tables** (1/1/0/1/3/0/3/10/0/21).

- [x] **Step 5b: Check the id sequences were reset.** `app.copy_db`'s `setval` has never run against live Postgres, because the live tests were skipped. Check it now, before cutover, rather than finding out from a failed admin create:

```bash
U="$(grep '^RAILWAY_DATABASE_URL=' .env | cut -d= -f2-)" uv run python -c "
import os; from sqlalchemy import create_engine, text
e = create_engine(os.environ['U'].replace('postgresql://', 'postgresql+psycopg://', 1))
with e.connect() as c:
    for t in ['profiles', 'experiences', 'achievements', 'skill_categories', 'skills', 'education', 'admin_users']:
        print(t, c.execute(text(f'SELECT max(id) FROM {t}')).scalar(), c.execute(text(f\"SELECT last_value FROM {t}_id_seq\")).scalar())"
```

Expected: on every line the two numbers are equal (`last_value` = `max(id)`).

**Result (2026-10-11):** All 10 sequences are correct: the next id is `max(id)+1`, and 1 for the empty tables. This confirms that `setval` works on live Postgres.

- [ ] **Step 6: Parity check.** *(not run; see annotation below)* The resume PDF is generated deterministically from content, so the bytes should be identical:

```bash
curl -s https://jacksoncareer.me/resume.pdf -o "$S/vm.pdf"
curl -s https://<RAILWAY_DOMAIN>/resume.pdf -o "$S/rw.pdf"
cmp "$S/vm.pdf" "$S/rw.pdf" && echo IDENTICAL
for p in / /about /experience /skills /education /contact; do
  diff <(curl -s https://jacksoncareer.me$p) <(curl -s https://<RAILWAY_DOMAIN>$p) >/dev/null && echo "$p same" || echo "$p DIFF"
done
```

Expected: `IDENTICAL` and every page `same`. Then log in as admin on `<RAILWAY_DOMAIN>` with the existing password. This proves the copied hash works.

**Annotation (2026-10-26, written afterward): not run, and it can't be run now.** No page or PDF comparison between the VM and Railway was recorded before the DNS cutover. The VM was deleted on 2026-10-13 (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, section 5), so there's no source left to compare against. What exists instead is the data-level comparison in Step 5: VM live, the backup, and Railway identical in all 10 tables, row by row and column by column. Since the pages and the PDF are generated from that data by the same code, identical data should give identical pages, but that's an inference, not a recorded check.

### Task 6: Cut DNS over to Railway [Jackson]

- [x] **Step 1:** Railway `web` → Networking → Custom Domain: add `jacksoncareer.me` and `www.jacksoncareer.me`. Note the records Railway shows (a CNAME target, plus a TXT verification record if it asks for one).
  - **Annotation (2026-10-26, written afterward):** Only `jacksoncareer.me` was added as a custom domain; Railway's trial allows one. Railway asked for the TXT record `_railway-verify.jacksoncareer.me`, created in Cloudflare at 02:05:07 UTC on 2026-10-11 (Cloudflare audit log). `www` later got a Cloudflare redirect instead (`docs/evidence/www-redirect.md`).
- [x] **Step 2:** At the DNS provider, replace the `A 52.159.85.45` records with Railway's records. The apex needs CNAME flattening or ALIAS support. If the registrar can't do that, move DNS to a provider that can, such as Cloudflare, before continuing.
  - **Annotation (2026-10-26, written afterward):** Cloudflare already hosted the zone (active since 2026-10-01 21:58 UTC, moved from Namecheap's `registrar-servers.com` nameservers), so no DNS move was needed. The root's `A 52.159.85.45` was replaced by `CNAME ctxkvml3.up.railway.app` at **01:51:12 UTC**, and `www`'s at 02:29:54 UTC (see *Record* below).
- [ ] **Step 3: Verify** (laptop) after Railway shows the certificate as issued: *(not recorded at the time; see annotation below)*

```bash
dig +short jacksoncareer.me www.jacksoncareer.me    # no longer 52.159.85.45
curl -sI https://jacksoncareer.me/ | grep -iE '^(HTTP|server|x-railway)'
curl -s https://jacksoncareer.me/api/v1/health
```

Expected: HTTP 200, Railway edge headers, health ok. Then make one admin edit and publish to prove writes land in Postgres.

**Annotation (2026-10-26, written afterward):** These checks weren't recorded on 2026-10-11. The earliest saved post-cutover evidence is the DNS snapshot of 2026-10-13 (`docs/evidence/dns-before-zoho.md`: both names CNAME to Railway). The equivalent checks were run on 2026-10-26 and are listed in *Record* below. The admin edit that proves writes land in Postgres wasn't recorded either. The "This Website (In Progress)" project row, added later and listed on the live `/projects`, shows writes do reach Postgres, but its date isn't recorded.

### Task 7: Record and hold the rollback

- [x] **Step 1:** Fill in a **Result** line under every step above. Add a final *Record* section: the deployed commit, the cutover time (UTC), the DNS records before and after. *(done 2026-10-26, afterward; see Record below)*
- [ ] **Step 2:** **Rollback** (until the VM is decommissioned): point DNS back to `A 52.159.85.45`. The VM is unchanged and still serves the pre-cutover content. Admin edits made on Railway after cutover would have to be re-applied or copied back by hand.
  - **Annotation (2026-10-26, written afterward):** **No longer possible.** The VM was deleted on 2026-10-13 at 23:03 UTC (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, section 5). Railway Postgres is the only copy of the data. A Railway-only rollback procedure is a separate TASKS.md item.
- [x] **Step 3:** Commit the plan doc with its results. Decommissioning the VM gets its own plan once Railway has run cleanly for 7 days. *(results committed 2026-10-26; the VM was decommissioned on 2026-10-13 without its own plan, at the instructor's direction)*

```bash
git add docs/superpowers/plans/2026-10-10-railway-postgres-migration.md
git commit -m "Record Railway migration results"
```

## Record (written 2026-10-26, after the cutover)

Reconstructed from the Cloudflare audit log (`cf audit-logs list --zone-name jacksoncareer.me`), Git history, and certificates. Nothing in this section was written on the day.

**Cutover timeline (2026-10-11, UTC)**

| Time | Change | Source |
|---|---|---|
| 00:14–00:21 | Migration code and this plan committed (`f5fa2d1` … `7cd922f`) and pushed to `main` | Git |
| 00:26:35 | VM database backup taken (Task 5 Step 4) | Step 4 Result |
| after 00:26 | Data copied into Railway Postgres and compared: identical in all 10 tables (Task 5 Step 5) | Step 5 Result |
| **01:51:12** | Root: `A 52.159.85.45` (VM) deleted, `CNAME ctxkvml3.up.railway.app` created, DNS only | Cloudflare audit log |
| 02:05:07 | `TXT _railway-verify.jacksoncareer.me` created, so Railway could verify the domain | Cloudflare audit log |
| ~02:06 | Railway's Let's Encrypt certificate issued. Its `notBefore` is 01:07:07, and Let's Encrypt backdates `notBefore` by roughly an hour, so issuance was most likely just after the TXT record. Inferred, not observed. | `openssl`, 2026-10-26 |
| 02:29:54 | `www`: `A 52.159.85.45` deleted, `CNAME ctxkvml3.up.railway.app` created, DNS only | Cloudflare audit log |

**Deployed commit at cutover:** most likely `7cd922f`. It's the last commit on `main` before the cutover, and no commits followed until 2026-10-13. Railway's deployment list no longer reaches back to 2026-10-11, so the deployment itself can't be confirmed.

**DNS before and after**

| Name | Before (until 2026-10-11) | After the cutover | Now (2026-10-26) |
|---|---|---|---|
| `jacksoncareer.me` | `A 52.159.85.45`, DNS only | `CNAME ctxkvml3.up.railway.app`, DNS only | same |
| `www.jacksoncareer.me` | `A 52.159.85.45`, DNS only | `CNAME ctxkvml3.up.railway.app`, DNS only | proxied placeholder + redirect to the root |
| `_railway-verify` | — | TXT added | same |

`www` didn't go straight from Railway to the redirect. On 2026-10-13 at 22:22 UTC the redirect rule was created, and at 22:25:56 `www` was changed to `A 52.159.85.45` (the VM), DNS only, so the rule couldn't run. The VM was deleted at 23:03, which left `www` broken until it was proxied on 2026-10-26 (`docs/evidence/www-redirect.md`). A `www` CNAME to Railway between 2026-10-11 and 2026-10-13 probably didn't serve the site either, since `www` was never added to Railway as a domain. Not verified.

**Post-cutover checks**
- 2026-10-11: none recorded.
- 2026-10-13: DNS snapshot (`docs/evidence/dns-before-zoho.md`).
- 2026-10-26: `/`, `/about`, `/projects`, health → 200 from Railway deployment `6c1e4147`. Railway certificate valid, `Verify return code: 0` (`docs/how-this-site-is-secured.md`, Railway addendum). Full DNS check (`docs/evidence/dns-final.md`). Database failure → 503 → recovery → 200 (`TASKS.md`, final section).

**Rollback:** the plan's rollback (DNS back to the VM) held until the VM was deleted on 2026-10-13 at 23:03 UTC. From then on, Railway was the only copy.

## Out of scope (follow-ups)

- The session cookie is set with `secure=False` (`app/main.py`, login). Making it `secure` in production is worth doing, but it's unrelated to the move.
- pytest overwrites `data/public-profile.json`. This is a known issue that predates this plan.
- VM decommission (Azure resources, NSG rules, Let's Encrypt cert).
