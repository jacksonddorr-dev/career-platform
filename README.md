# Career Platform

**Live site: https://jacksoncareer.me** (`www.jacksoncareer.me` redirects there)

My personal career site: a FastAPI app that shows my profile, experience, education, skills, and projects, and a downloadable résumé PDF, all read from a database when the page is requested. A small authenticated admin API edits the content. It started in Codespaces in September 2026, ran on an Azure Ubuntu VM with nginx, systemd, and SQLite, and since 2026-10-11 runs on Railway with PostgreSQL. Email for the domain goes through Zoho Mail, and visits are measured with Google Analytics 4 after the visitor consents.

The Project 1 evidence is indexed in [`docs/project-1-submission.md`](docs/project-1-submission.md).

**Contents**

- Set up and run locally: [Local development](#local-development), [Checks](#checks)
- Update the live site: [Deploys](#deploys) (every push to `main` deploys), [Service variables](#service-variables)
- [Architecture](#architecture): web, email, and analytics paths
- [Domains and DNS](#domains-and-dns)
- Outages and rollback: [Snapshot fallback and recovery](#snapshot-fallback-and-recovery), [Rolling back a bad change](#rolling-back-a-bad-change)
- Migration: [How the migration preserved the data](#how-the-migration-preserved-the-data), [Azure to Railway: who manages what](#azure-to-railway-who-manages-what)
- [Analytics (GA4)](#analytics-ga4)
- [Decisions](#decisions): Railway migration, managed email
- [Costs, credits, and cleanup](#costs-credits-and-cleanup)
- [Investigated failures](#investigated-failures) and [Remaining limitations](#remaining-limitations)
- [Reflection](#reflection)
- [Spec, plans, and history](#spec-plans-and-history)

## Architecture

Diagrams with locations, protocols, ports, and data flow are in [`docs/request-path.md`](docs/request-path.md):

1. **Azure (historical, 2026-09-29 to 2026-10-11):** browser → Cloudflare DNS (`A 52.159.85.45`) → Azure NSG (22 from my laptop, 80/443 from anywhere) → nginx on 80/443, where TLS ended → uvicorn (2 workers, systemd) on `127.0.0.1:8000` → SQLite file on the VM's disk.
2. **Railway (current):** browser → Cloudflare DNS (root CNAME, DNS only, flattened) → Railway's edge on 443, where TLS ends → app on port 8080 → PostgreSQL over Railway's private network. `www` is answered by Cloudflare's edge with a 301 to the root.
3. **Email:** Gmail → MX lookup → Zoho's MX servers (SMTP 25) → my mailbox. Replies go out through Zoho's servers, and receivers check SPF, DKIM, and DMARC in Cloudflare DNS.
4. **Analytics:** after the visitor allows it, the browser loads `gtag.js` from Google and sends events straight to Google Analytics over HTTPS, never through Railway.

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

### Rolling back a bad change

Written 2026-10-26. The code steps use standard Git and Railway features. The
**data steps are untested**: no backup has been taken or restored yet.

**No Azure rollback anymore.** The migration plan's rollback (point DNS back
to the VM at `52.159.85.45`) held until the VM was deleted on 2026-10-13 at
23:03 UTC. Since then Railway is the only place the site runs.

**Code**

1. **Normal path:** `git revert <bad-sha>`, then `git push origin main`. Railway
   rebuilds and deploys the revert like any other push. Check:
   - `railway deployment list` shows the new deployment as `SUCCESS`
   - the deploy log has `Wrote data/public-profile.json`
   - `/`, `/projects` and `/api/v1/health` return 200
2. **Emergency path:** in the Railway dashboard, open **Deployments**, choose
   the last good deployment, then **Rollback**. That redeploys the old image
   without a build. `main` still holds the bad commit, so the next push would
   bring it back: follow up with step 1.
3. **If the bad change included a migration:** `scripts/start.sh` runs
   `alembic upgrade head` on every boot, so rolling back code alone leaves the
   newer schema in place. Run `alembic downgrade <previous revision>` against
   production first, then roll back the code. That needs access to the
   database from inside Railway, which isn't set up yet (Postgres has no
   public proxy). Only one migration exists so far (`0001_initial`), and its
   downgrade has been tested on Postgres (commit `0ca8844`).

**Data**

Rolling data back needs a copy from before the change. **Right now there is
none: Railway Postgres is the only copy of the site's data.** Railway's
dashboard may offer volume backups; whether this plan includes them hasn't
been checked.

1. **Before any risky data or schema change**, take a dump and keep it
   outside Railway (not in Git: it contains the admin password hash), for
   example `pg_dump --format=custom` run from inside Railway's network.
2. **Freeze admin edits** until the change is verified, so nothing is written
   that a restore would lose.
3. **To roll back**, restore the dump into the production database
   (`pg_restore --clean`) and reload `/` to confirm the content.
4. **Data written after the dump** is lost by the restore. The site has one
   admin (me), so the fix is to re-enter those edits by hand through the
   admin API, from my own record of what I changed. If edits weren't frozen,
   compare a fresh dump of the bad state with the backup first to list them.

For an outage rather than a bad change, the database recovers on its own: see
*Snapshot fallback and recovery* above.

Never log or commit session secrets, administrator passwords, or database URLs.

## Azure to Railway: who manages what

The site ran on an Azure Ubuntu VM from 2026-09-29 and moved to Railway on 2026-10-11 (`docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`, *Record*). The VM was deleted on 2026-10-13. This table compares who was responsible for each layer.

| Layer | Azure VM (I managed) | Railway (Railway manages) | What's still mine on Railway |
|---|---|---|---|
| Operating system | Ubuntu 24.04 on the VM: packages, updates, users, SSH keys | The container base image Railpack builds on | Nothing at the OS level, and there's no SSH by default |
| Network and firewall | NSG rules: 22 from my laptop's IP only, 80 and 443 from anywhere. I updated the SSH rule whenever my IP changed. | Railway's edge and its private network between the app and Postgres | Nothing to configure |
| Runtime | System Python 3.12.3 plus a `uv` virtual environment I created | Railpack installs Python and packages at each build | Choosing versions: `.python-version` and `uv.lock` |
| Process management | A systemd unit (`Restart=always`, starts at boot) running uvicorn with 2 workers on `127.0.0.1:8000` | Starts the container, restarts it on failure (up to 5 times, `railway.json`), and waits for `/api/v1/health` before switching traffic | The start command (`scripts/start.sh`: migrate, snapshot, uvicorn with 2 workers on `$PORT`) |
| Web entry point | nginx I installed and configured on 80/443, forwarding to the app | Railway's edge, forwarding plain HTTP to the app on port 8080 | `--proxy-headers` so the app trusts the edge's `X-Forwarded-Proto` |
| TLS certificate | Let's Encrypt via certbot on the VM, renewed by a timer there; TLS ended at nginx | Let's Encrypt certificate issued and renewed by Railway; TLS ends at Railway's edge | Keeping the root DNS-only and pointed at Railway, and keeping `_railway-verify`, or renewal fails |
| Application code | `git pull` on the VM, then a service restart, by hand | Builds and deploys every push to `main` automatically | The code, and reviewing a change before pushing, since a push is a production deploy |
| Configuration and secrets | `.env` on the VM, `chmod 600` | Stores service variables and injects them | Setting them correctly. Until 2026-10-26 `SESSION_SECRET` and `SITE_URL` were missing, and nothing warned me. |
| Database software | SQLite: a library inside the app, no server | Runs a PostgreSQL 18.6 container with a volume | Schema changes (Alembic, run at every boot). Postgres version upgrades: not checked who owns these. |
| Data | One file on the VM's disk, backed up by me with `sqlite3 .backup` | Stores it on the Postgres volume | Backups. I haven't set up or verified any Railway backups, so Railway Postgres is currently the only copy. |
| DNS | Cloudflare records pointing at the VM's IP | Nothing | All of it: Cloudflare records, the `www` redirect, and the Zoho mail records |
| Logs and checks | `journalctl`, `ss`, `systemctl` over SSH | Keeps build and runtime logs (`railway logs`) | Reading them, and checking the site after each deploy |

**What Railway didn't take off my hands:** the parts that are specific to my site. That's code, configuration and secrets, data and its backups, DNS, schema migrations, dependency versions, and checking that a deploy worked. Three gaps showed up after the move:
- The service variables were incomplete for 15 days.
- `www` was broken from 2026-10-13 to 2026-10-26.
- There's no backup of the production database.

Platform deadlines are mine to track too: Railway stops supporting `railway.json` after 2026-12-01.


## Analytics (GA4)

The site uses Google Analytics 4, measurement ID `G-XWCRC21WXW`, and only after the visitor agrees. The code is the consent banner and tag at the end of `app/templates/base.html`. The Privacy page (`/privacy`) explains it to visitors.

**How a visit reaches Google Analytics**

1. Railway serves the page. Every page sets Google's Consent Mode default to `denied` (`analytics_storage`, `ad_storage`, `ad_user_data`, `ad_personalization`). Nothing is sent to Google, and `gtag.js` isn't loaded yet.
2. The banner asks the visitor. The choice is saved in the browser's `localStorage` as `analytics-consent`, so the banner doesn't reappear on every page.
3. **Allow:** the page calls `gtag('consent', 'update', {analytics_storage: 'granted'})`, then `gtag('config', 'G-XWCRC21WXW')`, and loads `gtag.js` from `www.googletagmanager.com`. **Decline:** nothing loads, and any `_ga` cookies are deleted.
4. `gtag.js` sends a `page_view` event, and GA4's **enhanced measurement** adds automatic events, including `click` for links to another domain (`outbound = true`). The site defines no custom events.
5. Each event is an HTTPS request **from the visitor's browser straight to Google** (`…google-analytics.com/g/collect`). It never passes through Railway or the app, which is why the server logs show none of it.
6. GA4 shows the events in **Realtime** within seconds, and in standard reports later.

**What the checks showed:** on 2026-10-25 at 8:10 PM PDT, after allowing analytics in a private window, I clicked the LinkedIn button. Realtime showed `page_view` for the visit and a `click` event with `link_domain = linkedin.com`, `link_url` set to my LinkedIn profile, and `outbound = true`. Enhanced measurement has Page views and Outbound clicks turned on. Details: `docs/evidence/ex06.md`, section 3.

**Limits**
- Visitors who decline, block scripts, or use an ad blocker aren't counted, so GA4 undercounts real visits.
- Counts of my own test visits are mixed in with real ones. No internal-traffic filter is set up.
- I didn't watch the `/g/collect` requests in the browser's Network tab, so the "nothing is sent before Allow" claim rests on the code and the Consent Mode default, not on an observed check.


## How the migration preserved the data

Records: [`docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`](docs/superpowers/plans/2026-10-10-railway-postgres-migration.md) (Task 5 results and the *Record* section).

1. **Plan first.** The plan and the migration code were committed 2026-10-11 00:14–00:21 UTC (`f5fa2d1` … `7cd922f`), before anything on the live site changed.
2. **Compatibility.** SQLite-to-Postgres differences were fixed and tested before the copy: the psycopg driver URL (`f5fa2d1`), a `%` in the password breaking Alembic (`f5fa2d1`), the `status` enum type left behind by downgrade (`0ca8844`), and id sequences after copying rows with their ids (`e4907ee`).
3. **Consistent source copy.** Admin edits were frozen and the VM database was copied with SQLite's online `.backup` at 00:26:35 UTC, checked by SHA-256 and `integrity_check`.
4. **Copy.** `python -m app.copy_db` copied every row into the empty, migrated Railway database, keeping ids, and refuses a target that already has rows.
5. **Comparison.** VM live, the backup, and Railway were compared table by table, row by row, and column by column: identical in all 10 tables. All 10 id sequences were checked: the next id is `max(id)+1`.
6. **Not re-seeded.** The seed script creates "Ada Analyst." The VM held my real résumé content, loaded 2026-09-30, and Railway has exactly that. See the Step 5 annotation in the plan.
7. **Cutover.** DNS moved at 01:51:12 UTC (Cloudflare audit log).

**Not done:** the rendered pages and PDF of the VM and Railway were never compared (plan Task 5 Step 6), and the VM is gone, so that comparison can't be made now.

## Decisions

> **Written 2026-10-26 from the repository's records.** I wrote both decisions in class, but those originals were lost. These reconstructions use the plans, commits, and evidence linked in each one, and the vendor facts were checked on 2026-10-26.

### 1. Move the site from the Azure VM to Railway with PostgreSQL

**Context.** The course required moving the running site from the Azure VM to Railway. The choices that remained were what database to use there, how to move the data, and how to switch over safely. Railway's trial lasts 30 days or $5 of usage and allows one custom domain.

**Alternatives considered**
- **Stay on the Azure VM.** I already knew how it worked, but I'd keep patching Ubuntu, nginx, certbot, and the NSG myself, and the course required the move.
- **Railway with SQLite.** It needed the fewest code changes, but a Railway container's filesystem is reset on every deploy, so a database file would be lost unless I attached and managed a volume for it.
- **Railway with PostgreSQL (chosen).** Railway runs the database as its own service on a private network, and the app already reached the database only through SQLAlchemy and one `DATABASE_URL`.
- **How to move the data:** re-run the seed script (rejected: it creates the demo "Ada Analyst" profile and would lose my real content), or copy every row from the VM's SQLite into Postgres with the same ids (chosen, `app/copy_db.py`, `e4907ee`).

**Reasons**
- Railway takes over the operating system, the web entry point, TLS certificates, and restarts (see *Azure to Railway: who manages what*).
- PostgreSQL avoids the reset-on-deploy problem and is the engine the original spec suggested ("PostgreSQL or equivalent").
- Copying rows with their ids keeps every record and its relationships exactly as on the VM, and can be checked row by row.
- Keeping the VM unchanged gave a rollback (point DNS back) until it was deleted on 2026-10-13.

**Trade-offs I accepted**
- Engine differences to fix first: the driver URL, the enum type, and id sequences (`f5fa2d1`, `0ca8844`, `e4907ee`).
- Less control and visibility: no SSH by default, and no database access from my laptop without extra setup.
- A short-lived platform: the trial ends, and the site moves again to AWS after the midterm.

**How it turned out.** The data arrived identical in all 10 tables and the cutover happened at 01:51:12 UTC on 2026-10-11 (*How the migration preserved the data*). The trade-offs also showed up: two service variables went unset for 15 days, and there's still no database backup.

### 2. Use managed email (Zoho Mail) instead of hosting my own

**Context.** I wanted a resume-ready address at my domain (`jackson@jacksoncareer.me`) that can send, receive, and reply, and passes SPF, DKIM, and DMARC.

**Alternatives considered**
- **Self-host a mail server** (for example Postfix and Dovecot) on the Azure VM.
- **Cloudflare Email Routing.** Free and already where my DNS is, but it only forwards incoming mail to another inbox. It can't send as `jackson@jacksoncareer.me`.
- **Google Workspace or Microsoft 365.** Full-featured, but paid per user.
- **Zoho Mail Forever Free (chosen).** One domain, up to 5 users, 5 GB per user, webmail only: IMAP, POP, and ActiveSync aren't included (zoho.com/mail pricing page, read 2026-10-26).

**Reasons**
- **Self-hosting wasn't workable on my subscription.** Azure blocks outbound SMTP on TCP port 25 from VMs for every subscription type except Enterprise Agreement and MCA-E (Microsoft Learn, "Troubleshoot outbound SMTP connectivity issues in Azure," read 2026-10-26), so my VM couldn't deliver mail directly to other servers. Running my own server would also have meant managing spam filtering, mail TLS, IP reputation, and security updates myself.
- **The VM was going away.** The site was moving to Railway, and Railway doesn't host mail servers. Email tied to the VM would have had to move again.
- **Managed email is separate from the website.** MX records send mail straight to Zoho, so moving the site from Azure to Railway didn't touch email.
- **It's free and does what the project needs:** send, receive, and reply from my domain, with SPF, DKIM, and DMARC.

**Trade-offs I accepted**
- Webmail only on the free plan, no IMAP client.
- My mail is stored by a third party under its terms.
- Deliverability depends on Zoho's servers and reputation.

**How it turned out.** Inbound mail arrived on 2026-10-13. A webmail reply on 2026-10-25 reached Gmail's Inbox in 5 seconds with SPF, DKIM, and DMARC passing for `jacksoncareer.me` (`docs/evidence/zoho-header-check.md`, `docs/evidence/ex06.md`).

## Costs, credits, and cleanup

Recorded 2026-10-25 (PDT). Balances come from each provider's dashboard, read by me, except where noted.

| Service | What it provides | Kind | Plan / credit | Spent so far | Expires or renews | Cleanup plan |
|---|---|---|---|---|---|---|
| **Railway** (project `prolific-enthusiasm`) | `career-platform` app service, Postgres service with its volume, custom domain | Compute (app, Postgres), **retained storage** (Postgres volume) | Free trial: $5 of credit, 30 days | $0.51 ($4.49 of $5 left) | **Trial ends 2026-11-06** | Move the site to AWS after the midterm, before 2026-11-06. Take a database dump first, since the Postgres volume holds the only copy of the data. After the move, delete the Railway project. Railway's Free plan doesn't allow a custom domain. |
| **Azure for Students** (through the GitHub Student Developer Pack) | Was the VM, OS disk, NIC, static public IP, NSG, and virtual network in `rg-career-platform` | Compute (VM, deleted), storage (OS disk, deleted), **network (static IP, still billed while it exists)** | $100 credit per year, renewable with valid student standing | $4.08 of $100 | Credit expires in 332 days, about **2027-09-22** | The VM, disk, and NIC were deleted 2026-10-13 as instructed. Still to do: release the static IP `vm-career-platform-ip` (nothing points to it since 2026-10-26) and delete the rest of `rg-career-platform`, once the instructor's cleanup directions confirm it. |
| **Namecheap** | Registration of `jacksoncareer.me` | Other (domain) | Free first year | $0 | Registered 2026-10-01; **renews 2027-10-01 for $23.98** | Decide before 2027-10-01 whether to renew. If it lapses, the site's address and the Zoho mailbox both stop working. |
| **Cloudflare** | Authoritative DNS, the `www` redirect, the edge certificate for `www` | Other (DNS) | Free plan (zone shows "Free Website", checked 2026-10-26) | $0 | No expiry | Keep. Nameservers stay delegated to Cloudflare. |
| **Zoho Mail** | Mailbox `jackson@jacksoncareer.me` | Retained storage (mail) | Free; I don't pay for it | $0 | No expiry stated | Keep. Its MX, SPF, DKIM, and DMARC records must stay in Cloudflare. |
| **Google Analytics 4** | Property `G-XWCRC21WXW` | Other (analytics) | Free | $0 | — | Keep. |
| **GitHub** | Public repository `jacksonddorr-dev/career-platform` | Other (source) | Free | $0 | — | Keep. |

- **Total spent so far:** $0.51 of Railway trial credit and $4.08 of Azure student credit. No money out of pocket.
- **The Azure figure is the portal's credit balance.** The usage API (`az consumption usage list`) reported $0.00 for the same resources, probably because student-credit usage isn't returned there. Not investigated further.

## Investigated failures

Each row links to the record with the symptom, checks, diagnosis, repair, and repeated check.

| Failure | Kind | Real or deliberate | Symptom → diagnosis → repair → re-check | Record |
|---|---|---|---|---|
| No `uv.lock` for `uv sync --locked` | Application dependency | Real (Azure build) | Plan assumed a lock file; `git ls-files` showed none → generated `uv.lock` on the laptop and committed it (`1e5ee06`) → `uv lock --check` exit 0, tests passed, VM installed 28 packages | [`docs/evidence/ex03.md`](docs/evidence/ex03.md) §3.1 |
| Other Azure build issues: tests overwriting the snapshot, unsaved `.env`, wrong PID file, false "running" check, SSH blocked after IP change | Application / network | Real | Each with what happened, how it was found, and what confirmed the fix | [`docs/evidence/ex03.md`](docs/evidence/ex03.md) §3.2–3.6 |
| Old A record and mismatched certificate after a move to Railway | DNS / TLS | **Deliberate, simulated lab** (given output; the repair was interpreted, not run) | `curl` error 60 → `dig` still returned the old A record → replace with Railway's CNAME → the expected output shows the CNAME and HTTP 200 | [`docs/evidence/ex05.md`](docs/evidence/ex05.md) |
| `www.jacksoncareer.me` not responding (2026-10-13 to 2026-10-26) | DNS | Real | `www` timed out → Cloudflare listed `www` as a DNS-only A record to the deleted VM, so the existing redirect rule never ran → made `www` a proxied placeholder → `curl` shows 301 to the root and 200, certificates verify | [`docs/evidence/www-redirect.md`](docs/evidence/www-redirect.md) |
| Railway build failed: "No start command detected" (2026-10-25) | Deployment / config | Real | Redeploy `a46a5e88` FAILED → Railpack wasn't reading the start command → added `railpack.json` (`7a2113b`) → uncached rebuild `2eb776be` SUCCESS, log shows `sh scripts/start.sh` | [`docs/evidence/postgres-password-rotation.md`](docs/evidence/postgres-password-rotation.md) |
| Database outage served stale content with 200 | Application / database | Found by audit; live check deliberate | Code served the snapshot with 200 → changed to 503 with "Projects temporarily unavailable" (`4afc2ee`) → live Postgres restart gave 11 × 503 then 200 with projects | [`docs/evidence/reviewed-change.md`](docs/evidence/reviewed-change.md); `TASKS.md` final section |
| Railway service variables missing (until 2026-10-26) | Configuration / security | Real | Canonical links pointed to `127.0.0.1`; a name-only variable listing showed only `DATABASE_URL`, so sessions were signed with the public default secret → set `SESSION_SECRET`, `SITE_URL`, `APP_ENV` → canonical correct, old-secret cookie gets 401 | Railway plan, Task 5 Step 1 annotation |

## Remaining limitations

- **No database backup.** Railway Postgres is the only copy of the site's data, and the data steps of the rollback procedure are untested.
- **No database access from the laptop.** Postgres has no public proxy, so migrations, dumps, and inspection would need `railway ssh` set up first.
- **Pre-cutover page and PDF parity was never checked**, and no checks were recorded on the cutover day (2026-10-11).
- **Azure evidence is incomplete:** no deliberate VM restart was recorded, and the certbot and nginx HTTPS configuration were never saved before the VM was deleted.
- **Admin activity isn't logged**, so whether anyone used the public default session secret before 2026-10-26 is unknown.
- **The site answers HEAD requests with 405** (GET-only routes), which can confuse uptime checkers and `curl -I`.
- **During the live outage test one request returned 200** mid-outage, most likely over a connection that hadn't closed yet. Not verified.
- **GA4 undercounts** visitors who decline or block scripts, and my test visits aren't filtered out.
- **No pre-MX email test** was done, so what happened to mail before MX existed isn't recorded.
- **Deadlines:** Railway stops supporting `railway.json` after 2026-12-01. The Railway certificate should renew around 2026-12-10, which should be checked.
- **The Azure static IP `52.159.85.45`** and its NSG and virtual network still exist in `rg-career-platform` and should be cleaned up.

## Reflection

Building my career platform showed me how many separate pieces have to work together for one website to run. I deployed it on Railway, managed the domain and DNS through Cloudflare, and set up many other services along the way. The most valuable aspect was learning to troubleshoot. After a security incident paused Railway deployments, I rotated my database credentials and learned why reference variables keep services in sync better than pasted connection strings. My next redeploy failed with a "no start command" error, even though the same code had worked minutes earlier. By comparing the two builds and working with the Claude coding agent, I was able to accurately troubleshoot and fix the problem. Using an AI agent made the work faster, but I still had to understand its reasoning and decide which actions to approve, especially with passwords and production deployments. If I did this again, I would record checks on the day instead of reconstructing them afterward. Overall, I feel much more confident building a system from start to finish and fixing it when something breaks.

## Spec, plans, and history

- Original design spec: [`docs/superpowers/specs/2026-09-15-career-platform-design.md`](docs/superpowers/specs/2026-09-15-career-platform-design.md). Section 12.1, added afterward, explains the SQLite choice.
- Implementation plan: [`docs/superpowers/plans/2026-09-15-career-platform-implementation.md`](docs/superpowers/plans/2026-09-15-career-platform-implementation.md)
- Azure VM migration plan: [`docs/superpowers/plans/2026-09-24-azure-vm-migration.md`](docs/superpowers/plans/2026-09-24-azure-vm-migration.md)
- Operate-the-VM plan (nginx, systemd, verification, and the decommission note): [`docs/superpowers/plans/2026-10-01-operate-the-vm.md`](docs/superpowers/plans/2026-10-01-operate-the-vm.md)
- Railway and PostgreSQL migration plan, which stands in for a separate spec: [`docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`](docs/superpowers/plans/2026-10-10-railway-postgres-migration.md)
- HTTPS write-up (Exercise 4, with Azure and Railway addenda): [`docs/how-this-site-is-secured.md`](docs/how-this-site-is-secured.md)
- Audit checklist and live outage record: [`TASKS.md`](TASKS.md)

Notes marked "written afterward" were added on 2026-10-26 while reconstructing this record. The plans' original steps are unchanged. Commit history: `git log --oneline` (the first commit is 2026-09-15).

