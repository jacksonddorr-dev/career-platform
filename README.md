# Career Platform

## Local development

This application uses Python 3.11+ and FastAPI. `uv` is optional; the commands
below use standard Python tooling.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"   # or: uv sync --extra test
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
pytest                       # with uv: uv sync --extra test && uv run pytest
python -m compileall app
```

`.python-version` pins Python 3.12 to match production. With uv, run
`uv sync --extra test` before `uv run pytest`, because a plain `uv run`
environment doesn't include the test tools.

`tests/test_postgres.py` holds live-Postgres tests that run only when
`TEST_DATABASE_URL` is set. They migrate up and down and insert rows, so point
the variable at a **scratch** database only. The fixture refuses any database
that is already migrated or has rows, so it can't run against production.

## Production on Railway

The site runs on [Railway](https://railway.com) in the project
`prolific-enthusiasm`, environment `production`, with two services:

| Service | What it is |
|---|---|
| `career-platform` | This app, built from GitHub `main` |
| `Postgres` | Railway-managed PostgreSQL, the app's only database |

### Deploys

**Every push to `main` deploys to production automatically**, because the
service is connected to `jacksonddorr-dev/career-platform`. Push to a branch if
you aren't ready to ship.

- **Build:** Railpack, configured in `railway.json`. It installs with
  `uv sync --locked --no-dev`, using Python from `.python-version`.
- **Start:** `scripts/start.sh` runs `alembic upgrade head` on every boot,
  writes the content snapshot with `python -m app.snapshot`, then runs
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`. Railway sets
  `PORT` (currently 8080).
- **Health check:** Railway waits for `GET /api/v1/health` to return 200 before
  it switches traffic to a new deploy. A failed migration exits the start script
  and Railway restarts it, up to 5 times.

Railway has deprecated `railway.json` ("config as code") in favour of
`.railway/railway.ts`. It keeps working until **2026-12-01**; migrate with
`railway config migrate` before then.

### Service variables

Variables on the `career-platform` service (checked by name 2026-10-26). Never commit their values.

| Variable | Set? | Value |
|---|---|---|
| `DATABASE_URL` | Yes | `${{Postgres.DATABASE_URL}}`, a reference that resolves to the private-network URL. The app converts `postgresql://` to the psycopg driver itself. |
| `SESSION_SECRET` | Yes, since 2026-10-26 | A long random value. It signs admin session cookies. **It must be set:** the default in `app/config.py` is public, and anyone could sign an admin cookie with it. To rotate it without printing it: `python3 -c 'import secrets;print(secrets.token_urlsafe(48), end="")' \| railway variable set SESSION_SECRET --stdin -s career-platform`. Rotating logs the admin out. |
| `SITE_URL` | Yes, since 2026-10-26 | `https://jacksoncareer.me`, used for the pages' `canonical` and `og:url` tags. Unset, they point to `http://127.0.0.1:8000`. |
| `APP_ENV` | Yes, since 2026-10-26 | `production` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | No, on purpose | Read only by `python -m app.seed` when creating the first admin in an empty database. The existing admin user and its password hash live in Postgres. |

Until 2026-10-26 only `DATABASE_URL` was set, so the site ran on the public default session secret and the wrong canonical URL. See `docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`, Task 5 Step 1.

### Domains and DNS

| Name | Served by |
|---|---|
| `jacksoncareer.me` | Railway, as a custom domain with a Railway-issued certificate |
| `career-platform-production-1a1e.up.railway.app` | Railway's generated domain |
| `www.jacksoncareer.me` | Cloudflare. A **proxied** placeholder A record (`192.0.2.1`) plus a redirect rule send `http://www` and `https://www` to `https://jacksoncareer.me` with a 301, keeping the path and query. See `docs/evidence/www-redirect.md`. |

The domain is registered at Namecheap, and its DNS is hosted on Cloudflare. The
root domain is a CNAME to the target Railway gives in `railway domain status
jacksoncareer.me`; Cloudflare flattens it at the apex. Records are DNS-only, not
proxied, so Railway issues and renews the certificate. `www` is the exception: it's proxied so Cloudflare can answer the redirect with its own edge certificate. Railway's ownership check
is the TXT record `_railway-verify.jacksoncareer.me`; keep it.

### Operating it from the command line

Install the Railway CLI (`brew install railway`). For `railway connect`, also
install `psql` with `brew install libpq` and put `/opt/homebrew/opt/libpq/bin`
on your `PATH`.

```bash
railway login
railway link --project prolific-enthusiasm --environment production --service career-platform
railway deployment list          # recent deploys and their status
railway logs                     # runtime logs of the current deploy
railway logs --build <deploy-id> # build logs
railway domain list              # read-only; bare `railway domain` CREATES a domain
railway connect Postgres         # psql session on the production database
```

DNS records can be listed with the Cloudflare CLI (`npm install --global cf`,
`cf auth login`, `cf dns records list --zone jacksoncareer.me`).

### Data

The VM's SQLite data was copied into Postgres on 2026-10-11 with
`python -m app.copy_db SOURCE_URL TARGET_URL`. The script copies every row into
an empty, migrated database, keeps ids, and resets the id sequences. It refuses
a target that has any rows. Run `python -m app.seed` only for a brand-new empty
database.

Railway Postgres is the only copy of the live data. The Azure VM and its
SQLite file were deleted on 2026-10-13, as the instructor directed after the
Railway migration.

### Snapshot fallback and recovery

The app keeps a snapshot of the published content at `SNAPSHOT_PATH` (default
`data/public-profile.json`). `scripts/start.sh` writes it from the database on
every boot, right after migrating, and each successful public request rewrites
it. The file is gitignored, so a deploy never starts from placeholder content.
If the boot can't write it (for example, no published profile), the app starts
without one.

| Situation | What a visitor gets |
|---|---|
| Database healthy | The page from the database, HTTP 200 |
| Database healthy, no projects published | "No projects are published yet.", HTTP 200 |
| Database read fails, snapshot exists | Profile from the snapshot, "Projects temporarily unavailable.", HTTP 503 on every public page. Snapshot projects are never shown. |
| Database read fails, no snapshot | HTTP 503 with no profile |

The resume PDF still comes from the snapshot during an outage, without
projects. Admin writes fail closed. The next request after the database
recovers returns 200 with projects, with no restart.

To recover:

1. Check `railway logs` and `GET /api/v1/health`. The health check doesn't
   touch the database, so a 503 on `/` with a 200 on health points at the
   database.
2. Restore database connectivity. Migrations run on the next boot, or redeploy
   to trigger them.
3. Reload `/` and confirm HTTP 200 with the projects listed.

**No Azure rollback anymore.** The migration plan's rollback (point DNS back
to the VM at `52.159.85.45`) stopped being possible when the VM was deleted on
2026-10-13. Only the VM's static public IP, NSG, and virtual network remain in
`rg-career-platform`. A rollback procedure for Railway code and data is still a
TASKS.md item.

Never log or commit session secrets, administrator passwords, or database URLs.