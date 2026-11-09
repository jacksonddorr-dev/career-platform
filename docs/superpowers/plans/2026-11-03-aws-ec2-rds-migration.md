# AWS EC2 + RDS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Tick each step and add a dated **Result** line as you go.

> **Status (2026-11-09): live on AWS since about 2026-11-09 23:06 UTC.** Tasks 1, 3, 4, 5 done; Task 6 done except Jackson's checks (admin login, Gmail send and reply, GA4 Realtime). Next is Task 7. **Step 1 is due before 2026-11-17 (token expiry).** No admin edits until Task 7. Task 2 Step 4 (second copy of the dump) is Jackson's and still open. Deviations are logged in `migration-notes.md`.

**Goal:** Serve https://jacksoncareer.me from an EC2 instance backed by a Single-AZ RDS PostgreSQL database, carrying over all data from Railway, with a tested way back and a tested way out when the course account closes.

**Architecture:** Browser → Cloudflare DNS (root `A` record, DNS only) → Elastic IP → EC2 security group (443/80) → nginx, where TLS ends → uvicorn on `127.0.0.1:8000` under systemd → RDS PostgreSQL over TLS on the VPC's private network. `www` and all mail records stay as they are. The app code barely changes.

**Tech Stack:** Ubuntu 24.04 (x86_64) on `t3.micro`, nginx, certbot, systemd, uv, Python 3.12, FastAPI, Alembic, psycopg 3, RDS for PostgreSQL 18.6 on `db.t3.micro`.

**Spec:** No separate spec doc. Requirements come from Jackson's request ("EC2 for the app and a Single-AZ RDS PostgreSQL database. Work on a new branch so Railway doesn't redeploy from main."), the decisions below, and the course assignment, which has **not been received yet**. Where the assignment conflicts with this plan, the assignment wins.

## Starting state (inspected 2026-11-03)

| Thing | Fact |
|---|---|
| Live site | Railway, returns 200. **Trial ends 2026-11-06.** Its Postgres is 18.6 with `en_US.utf8` sorting and no public endpoint. |
| Backup | `~/backups/career-platform/railway-20261029T220722Z.dump`, restore-tested 2026-10-29: 11 tables. It's stale once admin edits happen, and it exists only on the laptop. |
| AWS login | Profile `isba-4775`, IAM user `ISBA-student`, `us-east-1`. A course-owned account that ends with the term. |
| Passes dry run | `t3.micro`, `t3.small`, `AllocateAddress`, `CreateSecurityGroup`, `ImportKeyPair`, `RunInstances` with 20 GB gp3 and with IMDSv2 required |
| Denied | `t4g`, `t2`, `t3.medium` (explicit deny from `ISBA4775EC2Migration`); `CreateKeyPair`; EC2 Instance Connect; reading costs, budgets, and IAM |
| Not testable without creating something | `rds:CreateDB*`, IAM roles. RDS has no dry run. |
| Network | Only the default VPC, with a public subnet in each of six zones. `t3.micro` isn't offered in `us-east-1e`. |
| RDS | 18.6 available for `db.t3.micro` and `db.t4g.micro`. The default is 18.3, so the version must be explicit. `rds.force_ssl=1` in `default.postgres18`. |
| App | Stateless signed cookies, no uploaded files, one snapshot file on disk. `app/main.py:123` sets the session cookie with `secure=False`. |

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Hosting | EC2 + RDS, **Single-AZ** | Jackson's choice: learning, plus a managed database |
| Account lifetime | Temporary, course term only | Hence Task 8 and backups kept outside AWS |
| If 2026-11-06 is missed | Accept downtime, don't pay Railway | Jackson's choice. So the backup, not the switch, is the hard deadline (Task 2). |
| Who runs what | Claude prepares and explains. Jackson approves each stage and does console, dashboard, and browser steps. | Learning is the goal |
| Instance size | `t3.micro` with 1 GB swap and `CpuCredits=standard` | Smallest allowed; `standard` prevents surplus-credit charges |
| Network | Default VPC; RDS not publicly accessible; 5432 allowed only from the web security group | Simplest setup with the database still unreachable from the internet |
| Server login | SSH with an imported key, port 22 from Jackson's current IP only | Instance Connect is denied and Session Manager needs an IAM role we may not be able to create |
| Certificate | Issue through Cloudflare DNS before the switch, then change renewal to HTTP and delete the token | HTTPS can be fully tested before the switch, and no DNS-editing token stays on the server |
| Database logins | `career_admin` (RDS master, laptop only) and `career_app` (the app) | The app doesn't run with admin rights |
| Backups | **1-day** RDS backups (changed 2026-11-03: AWS's free plan rejected 7), deletion protection, plus dumps stored outside AWS as the real long-term backup | RDS backups disappear with the account, and can restore only about a day back |
| Deploys | Manual `deploy/deploy.sh` over SSH | GitHub Actions would need port 22 open beyond one IP. Out of scope. |

**Estimated cost, about $28.28/month** (730 hours, AWS public price lists read 2026-11-03, before any credits): `t3.micro` $7.59, `db.t3.micro` $13.14, 20 GB RDS gp3 $2.30, 20 GB EBS gp3 $1.60, public IPv4 $3.65. Backups and data transfer should be near $0. **`db.t3` always runs in Unlimited mode,** so sustained database CPU above its baseline bills extra at $0.075 per vCPU-hour. This login can't read the bill, so actual spend is unconfirmed.

## Questions for the instructor

Ask these before Task 3. Mark the affected steps blocked if there's no answer.

1. What does the assignment require: names, evidence, region, deadline?
2. What does `ISBA4775EC2Migration` allow for RDS instance classes, encryption, and storage?
3. What's the spending limit, who watches it, and can a budget alert be set?
4. On what date does the account close?

## Global Constraints

- **Branch:** all work is on `aws-ec2-rds-migration`. Nothing merges to `main` until Task 7, because every push to `main` deploys to Railway.
- **Region and profile:** `us-east-1`, `AWS_PROFILE=isba-4775`. Run `export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1 AWS_PAGER=""` in each new shell.
- **No secrets in git or in chat:** this repo is public. No passwords, tokens, database URLs with passwords, laptop IP, or account ID in committed files. Record generated values as `<EIP>`, `<RDS_ENDPOINT>`, and so on.
- **Instance limits:** only `t3.micro` or `t3.small`. PostgreSQL version is exactly `18.6`. `--no-multi-az` always.
- **Don't touch:** Railway's data, `www`, or the MX, SPF, DKIM, and DMARC records.
- **Tags:** `Project=career-platform` on everything that accepts tags.
- **Local Postgres tools:** `/opt/homebrew/bin` versions (18.6). Ubuntu's packaged client is older and can't read these dumps, so all dump and restore work runs from the laptop.

## Review Focus

1. **Plain HTTP request to the site or admin login.** Expected: 301 to HTTPS, and the session cookie carries `Secure`. Tests in Tasks 1 and 5.
2. **Database unreachable or rejecting TLS.** Expected: the same 503 snapshot behavior as Railway, no traceback to the visitor, and recovery with no restart. Test in Task 4.
3. **The EC2 instance reboots.** Expected: same IP, app and nginx return on their own, no manual step. Test in Task 4.
4. **A failed migration during deploy.** Expected: the app doesn't start on a half-migrated schema, and `deploy.sh` reports failure. Test in Tasks 1 and 4.
5. **Mail after the DNS change.** Expected: every non-root record is byte-identical and a test email still arrives. Test in Task 6.

---

## Stage A: Prepare on the branch (no AWS, no production change)

### Task 1: Code and deployment files ✅ Done 2026-11-09

**Files:**
- Modify: `app/main.py:123`
- Create: `deploy/career-platform.service`, `deploy/nginx-career-platform.conf`, `deploy/deploy.sh`, `scripts/db_fingerprint.sql`
- Test: `tests/test_web.py`, `tests/test_foundation.py`

**Interfaces:**
- Produces: `deploy/deploy.sh <git-ref>`, and `scripts/db_fingerprint.sql`, run with `psql -tA -F' ' -f`, printing one `table md5` line per public table and one `seq:name last_value` line per sequence.
- `scripts/start.sh` and `railway.json` stay unchanged, so Railway keeps working. systemd does the same jobs on EC2.

- [x] **Step 1: Write the failing cookie tests in `tests/test_web.py`**

  `test_login_cookie_is_secure_in_production`: set `APP_ENV=production` with `monkeypatch.setenv`, call `get_settings.cache_clear()`, log in with the `admin_user` fixture, then assert `"secure" in response.headers["set-cookie"].lower()`. Clear the cache again afterwards. `test_login_cookie_is_not_secure_in_development`: same with `APP_ENV=development`, asserting `"secure"` is absent, so local login over HTTP keeps working.

- [x] **Step 2: Run them.** `uv run pytest tests/test_web.py -k login_cookie -v`. Expected: the production test FAILS, the development test passes.
  - **Result (2026-11-09):** 1 failed (production), 1 passed, as expected.

- [x] **Step 3: Implement.** At `app/main.py:123`, use `secure=get_settings().app_env == "production"`. Railway already has `APP_ENV=production` and serves HTTPS, so this is safe there too.

- [x] **Step 4: Run them again.** Expected: both PASS.
  - **Result (2026-11-09):** 2 passed.

- [x] **Step 5: Write the failing deployment-file tests in `tests/test_foundation.py`**

  `test_ec2_service_binds_loopback_and_migrates_before_start` reads `deploy/career-platform.service` and asserts: contains `--host 127.0.0.1 --port 8000 --workers 2`; doesn't contain `0.0.0.0` or `forwarded-allow-ips`; has `ExecStartPre=` with `alembic upgrade head` before `ExecStart=`; the snapshot line starts `ExecStartPre=-`, so a failed snapshot can't block boot; has `Restart=always`, `WorkingDirectory=/home/ubuntu/career-platform`, and `User=ubuntu`. `test_ec2_nginx_redirects_http_and_forwards_proto` reads the nginx config and asserts it has `return 301 https://jacksoncareer.me$request_uri`, `listen 443 ssl`, `proxy_pass http://127.0.0.1:8000`, and `proxy_set_header X-Forwarded-Proto $scheme`.

- [x] **Step 6: Run them.** Expected: FAIL, files missing.
  - **Result (2026-11-09):** 2 failed, as expected.

- [x] **Step 7: Create `deploy/career-platform.service`**

  ```ini
  [Unit]
  Description=Career Platform (FastAPI via uvicorn)
  After=network-online.target
  Wants=network-online.target

  [Service]
  User=ubuntu
  Group=ubuntu
  WorkingDirectory=/home/ubuntu/career-platform
  ExecStartPre=/home/ubuntu/career-platform/.venv/bin/alembic upgrade head
  ExecStartPre=-/home/ubuntu/career-platform/.venv/bin/python -m app.snapshot
  ExecStart=/home/ubuntu/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```

  Why: the `-` lets a failed snapshot continue, while a failed migration stops the start. uvicorn trusts forwarded headers from `127.0.0.1` by default, which is exactly nginx, so the `'*'` from `start.sh` isn't needed here. It reads `.env` from the working directory.

- [x] **Step 8: Create `deploy/nginx-career-platform.conf`**

  Two server blocks for `server_name jacksoncareer.me`. Port 80: `location /.well-known/acme-challenge/ { root /var/www/html; }`, and everything else `return 301 https://jacksoncareer.me$request_uri;`. Port 443: `listen 443 ssl; listen [::]:443 ssl;`, `ssl_certificate` and `ssl_certificate_key` under `/etc/letsencrypt/live/jacksoncareer.me/`, `ssl_protocols TLSv1.2 TLSv1.3;`, and the `location /` proxy block from the Azure setup (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, Task 1.1 Step 2). No HSTS: this site moves again when the term ends.

- [x] **Step 9: Create `deploy/deploy.sh`** (POSIX `sh`, `set -eu`)

  Takes one argument, a git ref. It runs, in `~/career-platform`: `git fetch --all --prune`, `git checkout --detach <ref>`, `~/.local/bin/uv sync --locked --no-dev`, `sudo systemctl restart career-platform`. Then it checks `http://127.0.0.1:8000/api/v1/health` up to 30 times, 2 seconds apart. It prints the deployed `git rev-parse --short HEAD` and exits 0, or prints the last 30 `journalctl -u career-platform` lines and exits 1. To roll back, run it with the previous ref.

- [x] **Step 10: Create `scripts/db_fingerprint.sql`** from the query proven on 2026-10-29: for each public base table, `md5(coalesce(string_agg(r::text, E'\n' order by r::text collate "C"), ''))`, using `format(...)` and `\gexec`, then `pg_sequences` `last_value`. `collate "C"` is required, because Railway (`en_US.utf8`) and other servers sort differently, which produced false mismatches.

- [x] **Step 11: Run everything.** `uv run pytest` and `python -m compileall app`. Expected: all pass, Postgres-only tests skipped. Check `git status` for `data/public-profile.json` changes.
  - **Result (2026-11-09):** 35 passed, 2 skipped (Postgres-only); `compileall` OK; `sh -n deploy/deploy.sh` OK. The snapshot file is gitignored and unchanged.

- [x] **Step 12: Commit and push the branch**

  ```bash
  git add app/main.py tests deploy scripts/db_fingerprint.sql docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md
  git commit -m "Add EC2 deployment files and secure the session cookie in production"
  git push -u origin aws-ec2-rds-migration
  ```

  **Check:** `railway deployment list` shows no new deployment. A branch push shouldn't trigger one, but this is the first time we've relied on that, so confirm it.

### Task 2: Fresh backup before the trial ends — **hard deadline 2026-11-05**

Do this even if nothing else is ready. After the trial ends, this may be the only copy.

**Interfaces:** Produces `<DUMP>`, a checksummed, restore-tested dump outside the repo and outside AWS.

- [ ] **Step 1: Dump.** Where: laptop. Open the tunnel with `railway connect Postgres --tunnel-only -P 55432`, sending output to a private temp file because it prints the password. Run `pg_dump --format=custom --no-owner --file ~/backups/career-platform/railway-<UTC>.dump`, then `shasum -a 256` into a `.sha256` file. **Check:** exit 0 and `pg_restore --list` shows 11 `TABLE DATA` entries.
- [ ] **Step 2: Fingerprint production.** `psql ... -tA -F' ' -f scripts/db_fingerprint.sql > railway.fp`, kept outside the repo. Close the tunnel.
- [x] **Step 3: Test the restore locally.** Follow the 2026-10-29 method: a throwaway PostgreSQL 18.6 server on port 55433, using the Cellar binaries in `/opt/homebrew/Cellar/postgresql@18/18.6_1/bin`. Restore with `--no-owner --no-privileges --exit-on-error`. **Check:** `diff` against `railway.fp` is empty. Stop the server and delete its data.
  - **Result (2026-11-09):** Ran on the 2026-10-29 dump, since Railway is gone (`migration-notes.md` D3, D5). Checksum OK; `pg_restore --no-owner --no-privileges --exit-on-error` exit 0. The fingerprint (21 lines) is saved next to the dump as `railway-20261029T220722Z.fp`. All 11 table hashes equal the ones recorded in the 2026-10-29 session, where this restore matched production. Scratch server stopped and deleted.
- [ ] **Step 4: Second copy.** Jackson copies the dump and checksum to storage they control outside AWS (external drive or private cloud storage). **Check:** `shasum -a 256 -c` passes on the copy.

---

## Stage B: Create the AWS foundation — ⛔ **Jackson approves before starting; costs begin here**

### Task 3: Security groups and the RDS database ✅ Done 2026-11-09

RDS comes first because it's the most likely permission failure, and we want to learn that before anything else is built.

**Interfaces:** Produces `career-web-sg`, `career-db-sg`, `<RDS_ENDPOINT>`, database `career_platform`, logins `career_admin` and `career_app`.

- [x] **Step 1: Generate passwords.** Where: laptop. `python3 -c 'import secrets;print(secrets.token_hex(24))'`, twice. Jackson stores them in a password manager. Hex avoids characters that break URLs or RDS's password rules. Never print them in a shared log.
  - **Result (2026-11-03):** Generated both, stored in a mode-600 file outside the repo, never printed. Jackson still needs to copy them to a password manager.
- [x] **Step 2: Create the security groups.**
  ```bash
  VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
  WEB=$(aws ec2 create-security-group --group-name career-web-sg --description "career-platform web" --vpc-id $VPC --query GroupId --output text)
  DB=$(aws ec2 create-security-group --group-name career-db-sg --description "career-platform database" --vpc-id $VPC --query GroupId --output text)
  aws ec2 authorize-security-group-ingress --group-id $WEB --protocol tcp --port 22 --cidr "$(curl -s https://checkip.amazonaws.com)/32"
  aws ec2 authorize-security-group-ingress --group-id $DB --protocol tcp --port 5432 --source-group $WEB
  ```
  **Why:** 80 and 443 open at cutover prep (Task 5). The database rule names the web group rather than an IP, so it survives instance replacement. **Undo:** `aws ec2 delete-security-group`. **Check:** `describe-security-groups` shows exactly those rules.
  - **Result (2026-11-03):** Created `career-web-sg` (22 from one laptop IP) and `career-db-sg` (5432 from `career-web-sg` only). `describe-security-groups` shows exactly those rules.
- [x] **Step 3: Create the subnet group.** `aws rds create-db-subnet-group --db-subnet-group-name career-db-subnets --db-subnet-group-description "career-platform" --subnet-ids <us-east-1a subnet> <us-east-1b subnet>`. **Why:** RDS requires two zones even for Single-AZ. **If denied:** stop and take this to the instructor.
  - **Result (2026-11-03):** `career-db-subnets` is `Complete` with subnets in `us-east-1a` and `us-east-1b`.
- [x] **Step 4: Create the database.** Read the password into `$MASTER_PW` with `read -s` first.
  ```bash
  aws rds create-db-instance --db-instance-identifier career-platform-db \
    --db-instance-class db.t3.micro --engine postgres --engine-version 18.6 \
    --allocated-storage 20 --storage-type gp3 --storage-encrypted \
    --no-multi-az --availability-zone us-east-1a --no-publicly-accessible \
    --db-subnet-group-name career-db-subnets --vpc-security-group-ids $DB \
    --db-name career_platform --master-username career_admin --master-user-password "$MASTER_PW" \
    --backup-retention-period 1 --deletion-protection \
    --preferred-backup-window 09:00-09:30 --preferred-maintenance-window sun:10:00-sun:10:30 \
    --tags Key=Project,Value=career-platform
  ```
  **Why these flags:** same zone as the instance to avoid cross-zone charges; the backup and maintenance windows fall in the US night. **If denied:** read which flag or class the error names; `--storage-encrypted` may need KMS permissions. Don't drop encryption or change the class without Jackson's approval. **Check:** `aws rds wait db-instance-available`, then `describe-db-instances` shows `MultiAZ: false`, `PubliclyAccessible: false`, `EngineVersion: 18.6`, `BackupRetentionPeriod: 1`, `DeletionProtection: true`. **Undo:** remove deletion protection, then `delete-db-instance`.
  - **Result (2026-11-03): ⛔ Blocked, no database created.** `FreeTierRestrictionError`: "The specified backup retention period exceeds the maximum available to free tier customers." So the account is on AWS's free plan. The limit isn't documented anywhere I could find. Jackson chose 1-day backups.
  - **Result (2026-11-03, retry):** AWS accepted `--backup-retention-period 1`. Settings check pending.
  - **Result (2026-11-09):** Read back: `available`, `db.t3.micro`, 18.6, `MultiAZ: false`, `PubliclyAccessible: false`, encrypted, 20 GB gp3, `BackupRetentionPeriod: 1`, `DeletionProtection: true`, `us-east-1a`, `career-db-sg` active, CA `rds-ca-rsa2048-g1`.
- [x] **Step 5: Tick the Result lines.** Record the endpoint as `<RDS_ENDPOINT>` only.

  - **Result (2026-11-09):** Done; the endpoint is kept outside the repo.
### Task 4: EC2, the app, and a rehearsal restore ✅ Done 2026-11-09

**Interfaces:** Consumes Task 1's `deploy/` files, Task 2's `<DUMP>`, and Task 3's endpoint and groups. Produces the running service on `<EIP>`, reachable only through an SSH tunnel until Task 5.

- [x] **Step 1: Import the key.** `ssh-keygen -t ed25519 -f ~/.ssh/aws_career_platform -C career-platform`, then `aws ec2 import-key-pair --key-name career-platform --public-key-material fileb://~/.ssh/aws_career_platform.pub`.
- [x] **Step 2: Dry-run, then launch.** Get the AMI from `/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id`. Run with `--dry-run` first:
  ```bash
  aws ec2 run-instances --image-id $AMI --instance-type t3.micro --key-name career-platform \
    --security-group-ids $WEB --subnet-id <us-east-1a subnet> \
    --credit-specification CpuCredits=standard --metadata-options HttpTokens=required \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3,Encrypted=true}' \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=career-platform},{Key=Project,Value=career-platform}]'
  ```
  **If a flag is denied:** report it. Don't remove it silently. **Check:** `aws ec2 wait instance-status-ok`.
  - **Result (2026-11-03):** Key imported as `career-platform`. Dry run passed, then launched `t3.micro` in `us-east-1a` with Ubuntu 24.04.5. Read back: status checks OK, IMDSv2 required, `CpuCredits=standard`, 20 GB encrypted gp3, `career-web-sg`. SSH works and `uname -m` prints `x86_64`.
- [x] **Step 3: Attach an Elastic IP.** `allocate-address --domain vpc`, then `associate-address`. **Why:** without it the public IP changes on every stop and start, and DNS would break. **Undo, and it matters:** `release-address`; an unreleased address keeps billing. **Check:** `ssh -i ~/.ssh/aws_career_platform ubuntu@<EIP> uname -m` prints `x86_64`.
  - **Result (2026-11-09):** Laptop IP had changed, so the SSH rule was swapped first (`migration-notes.md` D6). Elastic IP allocated and attached; SSH works on it.
- [x] **Step 4: Prepare the server.** Where: EC2. `apt-get update && apt-get -y upgrade`; install `nginx certbot python3-certbot-nginx python3-certbot-dns-cloudflare`; add a 1 GB swapfile in `/etc/fstab`; install uv; set `Unattended-Upgrade::Automatic-Reboot "true"` with `Automatic-Reboot-Time "11:00"` (UTC). Download `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` to `/etc/ssl/certs/rds-global-bundle.pem`. **Check:** `free -h` shows swap; `python3 --version` is 3.12.x.
  - **Result (2026-11-09):** Packages installed (nginx 1.24.0, certbot 2.9.0 with the Cloudflare plugin), 1 GB swap, uv 0.13.7, Python 3.12.3, automatic reboot at 11:00 UTC, RDS bundle (114 certificates). No reboot pending.
- [x] **Step 5: Create the app login.** Where: laptop, through `ssh -L 55434:<RDS_ENDPOINT>:5432 ubuntu@<EIP>`. Connect as `career_admin` to database `postgres` with `sslmode=require`, then run:
  ```sql
  CREATE ROLE career_app LOGIN PASSWORD :'app_pw';
  GRANT career_app TO career_admin;
  ALTER DATABASE career_platform OWNER TO career_app;
  ```
  **Why:** on PostgreSQL 15+ the database owner controls the `public` schema, so migrations work without admin rights. **Check:** `SELECT datcollate FROM pg_database WHERE datname='career_platform'` is `en_US.UTF-8`, matching Railway's sorting. If it differs, stop, because text sorts differently on the site.
  - **Result (2026-11-09):** `career_app` created and owns `career_platform`. Collation and ctype `en_US.UTF-8`, encoding UTF8. Connection uses TLS.
- [x] **Step 6: Rehearse the restore.** Where: laptop, same tunnel, as `career_app`, using 18.6 tools and `sslmode=require` (`verify-full` can't pass through a tunnel because the hostname differs): `pg_restore --no-owner --no-privileges --exit-on-error <DUMP>`. **Check:** fingerprint output matches the local restore from Task 2 Step 3. Record how long the restore took.
  - **Result (2026-11-09):** Restored the 2026-10-29 dump in 10 s, exit 0. Fingerprint matches `railway-20261029T220722Z.fp` (21 lines). All tables owned by `career_app`; `alembic_version` = `0001_initial`. This is also the final data load (D9).
- [x] **Step 7: Deploy the code.** Where: EC2. `git clone https://github.com/jacksonddorr-dev/career-platform.git ~/career-platform`, then `git checkout aws-ec2-rds-migration`, and `~/.local/bin/uv sync --locked --no-dev`.
  - **Result (2026-11-09):** Cloned the branch at `fc760ba`; `uv sync --locked --no-dev` OK.
- [x] **Step 8: Write `.env` with mode 600.** Must contain `DATABASE_URL=postgresql://career_app:<pw>@<RDS_ENDPOINT>:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem`, a newly generated `SESSION_SECRET`, `SITE_URL=https://jacksoncareer.me`, `APP_ENV=production`. **Why this matters:** missing variables went unnoticed on Railway until 2026-10-26, and the session secret default is public. **Check:** `.venv/bin/python -c "from app.config import get_settings as g; s=g(); print(s.app_env, s.site_url, s.session_secret!='change-me-in-production', s.database_url.split('@')[-1].split('/')[0])"` prints `production`, the site URL, `True`, and the endpoint, with no password.
  - **Result (2026-11-09):** Mode 600, never printed. Check prints `production`, the site URL, and `True` for the secret, `verify-full`, and an RDS hostname. `alembic current` over `verify-full` reports `0001_initial (head)`.
- [x] **Step 9: Install and start the service.** Copy `deploy/career-platform.service` to `/etc/systemd/system/`, `daemon-reload`, `enable --now`. **Check:** `curl -s 127.0.0.1:8000/api/v1/health` returns 200, and `ss -ltnp` shows uvicorn on `127.0.0.1:8000` only.
  - **Result (2026-11-09):** Enabled and active. Health 200. `ss` shows the app on `127.0.0.1:8000` only (nginx's default site on :80, closed by the security group). Snapshot written at boot.
- [x] **Step 10: Check every page.** Use `ssh -L 8000:127.0.0.1:8000`. **Check:** `/`, `/about`, `/experience`, `/projects`, `/skills`, `/education`, `/contact` return 200 with real content, and `/resume.pdf` is a valid PDF.
  - **Result (2026-11-09):** All pages plus `/privacy` return 200 with real content; projects come from the database; canonical is `https://jacksoncareer.me/`; `/resume.pdf` is a 1-page PDF.
- [x] **Step 11: Test the failure cases.** (a) Reboot: `sudo reboot`. **Check:** same `<EIP>`, service active, health 200, with no manual step. (b) Database outage: temporarily remove the 5432 rule from `career-db-sg`. **Check:** public pages return 503 with the profile and "Projects temporarily unavailable." and no traceback. Restore the rule. **Check:** 200 with projects, no restart. (c) Bad migration: run `deploy.sh` on a scratch branch whose migration raises an error. **Check:** it exits 1, logs show the failure, and `deploy.sh <previous sha>` recovers.

---

  - **Result (2026-11-09):** (a) Reboot: boot time changed, same Elastic IP, app and nginx active, health 200, no manual step. (b) Outage, simulated with the server's firewall instead of the security group (D7): `/`, `/about`, `/projects` 503 with the profile and the outage message, no traceback; `/resume.pdf` 200 from the snapshot; after unblocking, 200 with projects, 0 restarts. (c) Bad migration: the app didn't start, `deploy.sh` exited 1 but printed no reason, so it was fixed (`9fcc825`, D8). Re-run prints the reason and the migration error; rollback to `9fcc825` OK; database fingerprint unchanged; `0001_initial (head)`.
## Stage C: Switch — ⛔ **Jackson approves before starting**

### Task 5: HTTPS before the switch

- [x] **Step 1: Issue the certificate through DNS.** Jackson creates a Cloudflare API token limited to DNS Edit on `jacksoncareer.me`, saved to `/root/.secrets/cloudflare.ini` with mode 600. Check no `CAA` record blocks Let's Encrypt. Run `sudo certbot certonly --dns-cloudflare --dns-cloudflare-credentials /root/.secrets/cloudflare.ini -d jacksoncareer.me`. **Why:** the site's DNS still points at Railway, so the usual HTTP challenge can't reach this server yet. **Check:** files exist under `/etc/letsencrypt/live/jacksoncareer.me/`, and certbot added a temporary `_acme-challenge` record and removed it.
  - **Result (2026-11-09):** Jackson created the token in the dashboard: DNS Edit on this zone only, restricted to the Elastic IP, expiring 2026-11-17 07:59 UTC (D11). File is `600 root`. Cloudflare verify: active, zone visible. No CAA record. A dry run passed, then the real certificate was issued: CN `jacksoncareer.me`, Let's Encrypt `YE1`, expires 2027-02-07. 0 leftover `_acme-challenge` records. Renewal is still set to `dns-cloudflare` until Task 7 Step 1.
- [x] **Step 2: Install nginx config and open the ports.** Install `deploy/nginx-career-platform.conf` as the only enabled site; `nginx -t`; reload. Add 80 and 443 from `0.0.0.0/0` (and `::/0` only if the instance gets IPv6) to `career-web-sg`.
  - **Result (2026-11-09):** Only site enabled is `career-platform` (default removed); `nginx -t` OK; reloaded. 80 and 443 opened to `0.0.0.0/0`; no IPv6 on the instance, so no `::/0`.
- [ ] **Step 3: Test without touching DNS.**
  ```bash
  curl -sI --resolve jacksoncareer.me:443:<EIP> https://jacksoncareer.me/
  curl -sI --resolve jacksoncareer.me:80:<EIP> http://jacksoncareer.me/about
  ```
  **Check:** HTTPS 200 with a valid certificate; HTTP 301 to `https://jacksoncareer.me/about`. Run the same for every page. Log in with a `--resolve` POST using Jackson's password. **Check:** the `Set-Cookie` header has `Secure` and `HttpOnly`, and an admin read returns 200.

  - **Result (2026-11-09):** All checks pass except one. Certificate verifies; TLS 1.0 and 1.1 refused; every page plus `/privacy` 200 with real content; canonical and `og:url` are `https://jacksoncareer.me/`; HTTP returns 301 to HTTPS keeping path and query; `/admin` 401 unauthenticated; wrong password 401 with no cookie. **Still open:** a real admin login to confirm `Secure; HttpOnly` on the cookie. Needs Jackson's password.

### Task 6: Cutover

**Rollback until Task 7:** change the root record back to the saved Railway CNAME. It works only while the Railway trial is alive, and any edits made on RDS after the switch would be lost, so **no admin edits until Task 7.**

- [x] **Step 1: Record the starting DNS.** Save `dig` output through `1.1.1.1` for root, `www`, MX, and the SPF, DKIM, and DMARC TXT records, plus the current root CNAME target, in `dns-before.txt`, outside the repo.
  - **Result (2026-11-09):** Saved to `~/backups/career-platform/dns-before-20261109.txt` (outside the repo): `dig` answers through 1.1.1.1 plus the full Cloudflare record list (10 records; root was `CNAME ctxkvml3.up.railway.app`, DNS only). The zsh word-splitting bug emptied the first attempt's `dig` answers; it was rerun in bash.
- [x] **Step 2: Freeze edits and repeat the Task 2 dump.** Jackson makes no admin edits from here. Fingerprint production again. If it differs from `railway.fp`, take a new dump. Close the tunnel.
  - **Result (2026-11-09):** Replaced by D9: Railway is gone and there were no edits after 2026-10-29. Jackson makes no admin edits until Task 7.
- [x] **Step 3: Load the final data.** Stop the app. As `career_admin` through the tunnel: `DROP DATABASE career_platform WITH (FORCE); CREATE DATABASE career_platform OWNER career_app;`. Restore as `career_app`. **Check:** fingerprint equals the Step 2 production fingerprint. Start the app, repeat Task 5 Step 3. **Deletion protection** applies to the instance, not this drop, so double-check you're connected through port 55434 to `career_platform`.
  - **Result (2026-11-09):** Replaced by D9: no re-restore. The RDS fingerprint still matches the reference (21 lines); HTTPS health 200 before the switch.
- [x] **Step 4: Switch DNS.** Jackson, in Cloudflare: replace the root `CNAME` with `A jacksoncareer.me <EIP>`, **DNS only**, TTL Auto. Nothing else changes.
  - **Result (2026-11-09):** Jackson replaced the root CNAME with `A jacksoncareer.me <EIP>`, DNS only, TTL Auto. Verified around 2026-11-09 23:06 UTC: 1.1.1.1, 8.8.8.8, and Cloudflare's own nameserver all answer `<EIP>`; Cloudflare still has 10 records.
- [ ] **Step 5: Verify from outside.**
  - `dig @1.1.1.1 +short jacksoncareer.me` returns `<EIP>`.
  - `curl -sI https://jacksoncareer.me/` returns 200 and the certificate verifies; every page and `/resume.pdf` return 200.
  - `curl -sI https://www.jacksoncareer.me/x` returns 301 to `https://jacksoncareer.me/x`.
  - Page `canonical` tags show `https://jacksoncareer.me`.
  - A consented visit appears in GA4 Realtime.
  - Comparing against `dns-before.txt`, the `www`, MX, SPF, DKIM, and DMARC answers are unchanged.
  - Jackson sends a test message from Gmail to `jackson@jacksoncareer.me` and replies. **Check:** both arrive.
  - **Result (2026-11-09):** Without `--resolve`: HTTPS reaches `<EIP>`, certificate verifies (Let's Encrypt `YE1`, until 2027-02-07); every page plus `/privacy` 200; `/resume.pdf` a 1-page PDF; canonical `https://jacksoncareer.me/`; GA4 tag `G-XWCRC21WXW` present; HTTP returns 301 to HTTPS; `www` (http and https) returns 301 to the root keeping path and query. AAAA, `www`, MX, SPF, Zoho verification, DMARC, DKIM, `_railway-verify`, CAA, and NS are identical to the snapshot. **Still open:** Jackson's Gmail send and reply, and GA4 Realtime.
- [ ] **Step 6: Confirm the app sees real traffic.** `journalctl -u career-platform` and the nginx access log on EC2 show the requests from Step 5.

---

## Stage D: Finish — ⛔ **Jackson approves deletions**

### Task 7: Harden, document, merge, retire Railway

- [ ] **Step 1: Move renewal to HTTP and remove the token.** **⏰ Must be done before 2026-11-17 07:59 UTC, when the token expires.** Otherwise the renewal around January fails. After DNS has settled: `sudo certbot reconfigure --cert-name jacksoncareer.me --nginx`, then `sudo certbot renew --dry-run`. **Check:** the dry run succeeds using HTTP. Delete `/root/.secrets/cloudflare.ini` and revoke the token in Cloudflare. **Why:** a compromised server holding that token could rewrite your DNS, including mail.
- [ ] **Step 2: Test an RDS restore.** Run `aws rds restore-db-instance-to-point-in-time` to a temporary `career-platform-db-drill` in the same subnet group, with the same security group, fingerprint it through the tunnel, then delete it **with no final snapshot**. **Why:** a backup isn't proven until it has been restored. Costs a few cents. **Check:** `describe-db-instances` no longer lists the drill instance.
- [ ] **Step 3: Set up monitoring.** Jackson adds a free external uptime check on `/api/v1/health` with email alerts. Ask whoever has billing access to set a budget alert (see *Questions for the instructor*).
- [ ] **Step 4: Update the record.** Revise `README.md` (live architecture, deploys, variables, domains, costs, limitations, including "No database backup"), `docs/request-path.md`, and add `docs/evidence/aws-migration.md` with commands and results, no secrets. `uv run pytest`.
- [ ] **Step 5: Merge to `main` — ⛔ ask first.** This will trigger a Railway deploy if Railway is still connected. The change is safe there, but do it only after cutover is verified.
- [ ] **Step 6: Retire Railway — ⛔ ask first; can't be undone.** Wait until the site has run on AWS for at least 48 hours with no problems, or the trial has ended. Confirm you have the Task 6 dump. Delete the Railway project, the `_railway-verify` TXT record, and the SSH key (`railway ssh keys remove`, then delete `~/.ssh/railway_ed25519*`). `railway.json`, `railpack.json`, `scripts/start.sh`, and their tests can go in a later cleanup.

### Task 8: The way out before the course account closes

Write this into the calendar once the instructor gives the closing date. Start **at least two weeks** before it. This plan doesn't choose the next host.

- [ ] **Step 1: Dump and verify.** Through the SSH tunnel, as `career_app`, with the 18.6 tools. Fingerprint, test-restore locally, and store outside AWS as in Task 2.
- [ ] **Step 2: Move the site** to its next home and repoint the root record. Without a next home, the site stays down and the domain and mail stay active, because mail doesn't depend on AWS. The domain renews 2027-10-01.
- [ ] **Step 3: Delete in this order — ⛔ ask first.** Terminate the instance; `release-address` (a forgotten address keeps billing); `modify-db-instance --no-deletion-protection`, then `delete-db-instance`; delete leftover snapshots; `delete-db-subnet-group`; both security groups, `career-db-sg` first after removing its rule; `delete-key-pair`. **Check:** `describe-instances`, `describe-addresses`, `describe-db-instances`, and `describe-db-snapshots` all come back empty.

---

## Not in this plan

- Automatic deploys from GitHub, a load balancer, Multi-AZ, Secrets Manager, CloudWatch agent, Infrastructure as Code. Some are denied; none is needed for one small site this term.
- Releasing the Azure static IP (`vm-career-platform-ip`), which the README tracks separately. It's still worth doing.
- `alembic/Current_resume.pdf`, `.cloudflare/`, and `.impeccable/` are untracked and stay out of commits. Task 1 Step 12 stages named paths only.
