# Career Platform

## Local development

This application uses Python 3.11+ and FastAPI. `uv` is optional; the commands
below use standard Python tooling.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
uvicorn app.main:app --reload
```

Create the schema and representative profile with:

```bash
alembic upgrade head
python -m app.seed
```

The application is available at `http://127.0.0.1:8000`. Public pages include
`/`, `/about`, `/experience`, `/projects`, `/skills`, `/education`, `/contact`,
and `/resume.pdf`. The health check is at `GET /api/v1/health`.

Copy `.env.example` to `.env` to override non-secret runtime settings. Secrets
must be supplied through the deployment environment and must not be committed.

## Checks

```bash
pytest
python -m compileall app
```

## Deployment and recovery

Set `DATABASE_URL`, `SESSION_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and
`SITE_URL` in the deployment environment. Run `alembic upgrade head` during
release, then run `python -m app.seed` only for a new empty database. A
successful public request writes the latest published content to
`SNAPSHOT_PATH` (default `data/public-profile.json`); preserve that file with
the deployment artifact or persistent volume.

If the database is unavailable, public pages and the resume use the last
successful snapshot while admin writes fail closed. Verify `/`, `/resume.pdf`,
and `/api/v1/health`, restore database connectivity, run migrations if needed,
and request the public page once to refresh the snapshot. Never log or commit
session secrets or administrator passwords.