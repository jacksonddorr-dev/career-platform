# Evidence: Railway → AWS (EC2 + RDS), 2026-11-03 to 2026-11-09

Checks run during the move, with their results. The full step-by-step record is the plan, [`docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md`](../superpowers/plans/2026-11-03-aws-ec2-rds-migration.md), whose **Result** lines carry the details. Deviations from it are in [`migration-notes.md`](../../migration-notes.md). No passwords, IP addresses, or connection strings appear here; `<EIP>` is the instance's Elastic IP, which `dig jacksoncareer.me` returns.

## Account limits found before building (2026-11-03)

Read-only calls and `--dry-run` launches as IAM user `ISBA-student`:

| Request | Result |
|---|---|
| `run-instances --dry-run`, `t3.micro` / `t3.small` | `DryRunOperation` (would succeed) |
| `run-instances --dry-run`, `t4g.*`, `t2.micro`, `t3.medium` | Explicit deny from the course policy `ISBA4775EC2Migration` |
| `create-key-pair` / EC2 Instance Connect | Denied; `import-key-pair --dry-run` succeeds |
| Pricing, Cost Explorer, Budgets, Free Tier | Denied |
| `create-db-instance` with `--backup-retention-period 7` | `FreeTierRestrictionError`; 1 day accepted |

## What was built, read back from AWS

| Resource | Read-back (2026-11-09) |
|---|---|
| RDS `career-platform-db` | `available`, `db.t3.micro`, PostgreSQL 18.6, `MultiAZ: false`, `PubliclyAccessible: false`, encrypted, 20 GB gp3, retention 1 day, deletion protection on, `us-east-1a`, CA `rds-ca-rsa2048-g1` |
| EC2 `career-platform` | `t3.micro`, Ubuntu 24.04.5, `x86_64`, IMDSv2 required, `CpuCredits=standard`, 20 GB encrypted gp3, Elastic IP attached |
| `career-web-sg` | 22 from one laptop `/32`; 80 and 443 from `0.0.0.0/0` |
| `career-db-sg` | 5432 from `career-web-sg` only |
| Database | owner `career_app`; collation and ctype `en_US.UTF-8` (same as Railway's) |

## Data carried over

- **Source:** `railway-20261029T220722Z.dump`, the last dump before Railway went down (checksum OK). Jackson confirmed no edits after it.
- **Reference fingerprint:** restored locally into PostgreSQL 18.6 and fingerprinted with `scripts/db_fingerprint.sql` (one md5 per table over all rows in byte order, plus sequence values). The 11 table hashes equal those recorded on 2026-10-29, when this restore matched live Railway.
- **RDS restore:** `pg_restore --no-owner --no-privileges --exit-on-error` as `career_app`, 10 s, exit 0. Fingerprint identical to the reference (21 lines). Re-checked identical just before the DNS switch and after the bad-migration test.

## Server and failure tests (2026-11-09)

| Test | Result |
|---|---|
| App config | `production`, `https://jacksoncareer.me`, non-default secret, `sslmode=verify-full`, RDS hostname; `alembic current` over `verify-full` → `0001_initial (head)` |
| Listening ports | uvicorn on `127.0.0.1:8000` only; nginx on 80 and 443 |
| Reboot | Boot time changed; same `<EIP>`; app and nginx active; health 200 with no manual step |
| Database outage (outbound 5432 rejected on the instance) | `/`, `/about`, `/projects` → 503 with the profile and "Projects temporarily unavailable.", no traceback; `/resume.pdf` 200; after unblocking → 200 with projects, 0 restarts |
| Failing migration via `deploy.sh` | App didn't start; first run exited 1 without the reason (bug, fixed in `9fcc825`); re-run printed "service failed to start" and the migration error; `deploy.sh <good sha>` recovered; data unchanged |

## HTTPS and cutover (2026-11-09)

| Check | Result |
|---|---|
| Certificate | Issued through a Cloudflare DNS challenge after a passing dry run; CN `jacksoncareer.me`, Let's Encrypt `YE1`, expires 2027-02-07; no `_acme-challenge` left behind |
| Before DNS, with `curl --resolve` to `<EIP>` | Certificate verifies; TLS 1.0/1.1 refused; every page 200; canonical and `og:url` `https://jacksoncareer.me/`; HTTP → 301 HTTPS keeping path and query; `/admin` 401; wrong password 401 with no cookie |
| DNS switch | Root `CNAME` (Railway) replaced by `A <EIP>`, DNS only. 1.1.1.1, 8.8.8.8, and Cloudflare's nameserver answer `<EIP>`. Every other record identical to the pre-switch snapshot (10 records before and after). |
| After DNS, without `--resolve` | Every page 200 from `<EIP>`, certificate verifies, GA4 tag present, `www` → 301 to the root keeping path and query |
| Jackson's checks | Gmail → Zoho and the reply both arrived; the visit showed in GA4 Realtime |
| Renewal moved off the token | `certbot reconfigure --webroot -w /var/www/html --deploy-hook "systemctl reload nginx"`; token file shredded; `certbot renew --dry-run` succeeds without it; nginx config unchanged |

## RDS restore test (2026-11-09)

Point-in-time restore of `career-platform-db` to its latest restorable time, as a temporary `career-platform-db-drill`. About 18 minutes to `available`. Fingerprint through an SSH tunnel identical to the reference (21 lines, 11 tables). Deleted afterwards, with no snapshot or backups left behind.

## `aws.jacksoncareer.me` (2026-11-09)

Added at Jackson's request (`migration-notes.md` D13, D14): `A aws → <EIP>`, DNS only. The zone diff shows one record added, nothing else changed. A separate Let's Encrypt certificate was issued over HTTP. `https://aws.jacksoncareer.me/` returns 200 with a verifying certificate; HTTP returns 301 to HTTPS on that name.
