

# Azure VM Migration Implementation Plan

> **Redacted for publishing:** the VM's public IP, the laptop IPs, the email address, the SSH key file name, and the host-key fingerprint are replaced with `<PLACEHOLDERS>`. The real values live in Azure and `~/.ssh`.

> **Status (2026-09-29): ✅ All 8 sections complete.** The app runs on `vm-career-platform` (uvicorn pid 14981 since the ~22:44 UTC restart, `0.0.0.0:8000`) with the migrated data. **2026-09-30:** The site now shows Jackson's real resume on both the laptop and the VM (Section 9). uvicorn pid 1727, `0.0.0.0:8000`. It's publicly reachable at `http://<VM_PUBLIC_IP>:8000` via the NSG rule `Temp-HTTP-8000` (open to `*`, not created by Claude). The SSH rule now allows `<LAPTOP_IP>/32`. Still open: uvicorn isn't a systemd service, so it won't survive a reboot; and `pytest` overwrites `data/public-profile.json` (see Task 3.1).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the career platform on the Azure VM `vm-career-platform`, serving the same SQLite data the laptop has today.

**Architecture:** The code is cloned from GitHub onto the VM. `uv` installs a locked virtualenv. The laptop's SQLite database is copied over with `scp`. `uvicorn` serves the app on `127.0.0.1:8000` on the VM. We verify with `curl` on the VM, then look at it in a laptop browser through an SSH tunnel. No inbound port other than 22 is opened.

**Tech Stack:** Ubuntu 24.04 LTS (Standard_B2ats_v2), Python ≥ 3.11 (Ubuntu 24.04 ships 3.12), uv, FastAPI + uvicorn, SQLAlchemy/Alembic, SQLite.

**Spec:** The migration outline Jackson gave on 2026-09-28 (Server → Packages → Code → Python → Config → Data → Processes → Verify). There is no separate spec file. App behavior is described in `README.md` and `docs/superpowers/specs/2026-09-15-career-platform-design.md`.

## Global Constraints

- VM: `vm-career-platform`, resource group `rg-career-platform`, region northcentralus, public IP `<VM_PUBLIC_IP>`.
- SSH always as `azureuser` with key `~/.ssh/<ssh-key>`:
  `ssh -i ~/.ssh/<ssh-key> azureuser@<VM_PUBLIC_IP>`
- Repo: `https://github.com/jacksonddorr-dev/career-platform` (public, so an HTTPS clone needs no credentials), branch `main`.
- App directory on the VM: `/home/azureuser/career-platform`. `DATABASE_URL` (`sqlite:///./career_platform.db`) and `SNAPSHOT_PATH` (`data/public-profile.json`) are **relative**, so uvicorn must be started from that directory.
- The laptop database is `/Users/jacksondorr/career-platform/career_platform.db`. It is gitignored and must never be committed.
- `.env` holds secrets. It is gitignored and must never be committed. `SESSION_SECRET` must not be the placeholder value.
- The NSG only allows TCP 22 from `<LAPTOP_IP_OLD>/32`. This plan does **not** open port 8000. ~~uvicorn binds to `127.0.0.1`.~~ **Changed 2026-09-29 at Jackson's request:** uvicorn binds to `0.0.0.0` (all IPv4 addresses) on port 8000. Nothing in Azure was changed, so the NSG still blocks 8000 from the internet.
- The migration is complete when `/api/v1/health` returns 200 on the VM and `/` shows the laptop's `profiles.full_name`.

## Review Focus

1. **There is no `uv.lock` in the repo.** `git ls-files` shows none, and uv isn't installed on the laptop. The outline says "uv sync from the lock file", so the lock has to be created and pushed before the clone (Code, step 1). Otherwise `uv sync --locked` fails on the VM.
2. **Laptop public IP changes.** The NSG only allows SSH from `<LAPTOP_IP_OLD>/32`. If the laptop is on another network, every SSH/scp step times out. The Server section checks this first.
3. **Copying a live SQLite file.** A raw `scp` taken while local uvicorn is writing can copy a torn file. The Data section stops local uvicorn, takes a `sqlite3 .backup`, and compares checksums and row counts on both ends.
4. **Starting uvicorn from the wrong directory.** The relative `DATABASE_URL` would create a new, empty `career_platform.db` wherever uvicorn is started, and the site would show no data without any error. The Processes section `cd`s explicitly, and Verify checks the profile name, not just HTTP 200.
5. **The uncommitted `data/public-profile.json`.** The laptop has local snapshot changes (`git status`: M). The VM gets the committed version, and the app rewrites it on the first successful public request. Don't sweep it into the `uv.lock` commit.

Out of scope, and noted so nobody assumes otherwise: running uvicorn as a systemd service (the process started here won't survive a reboot or logout-kill), HTTPS/domain, opening port 80/8000, backups.

---

## 1. Server

### Task 1.1: Confirm the VM is up and reachable over SSH ✅ Done 2026-09-29

- [x] **Step 1: Confirm the power state**
  - **Where:** laptop (or portal: Virtual machines → vm-career-platform → Overview → Status)
  - **Run:**
    ```bash
    az vm get-instance-view -g rg-career-platform -n vm-career-platform \
      --query "instanceView.statuses[?starts_with(code,'PowerState')].displayStatus" -o tsv
    ```
  - **Why:** Every later step needs a running VM.
  - **Check:** Prints `VM running`. If it prints `VM deallocated`, run `az vm start -g rg-career-platform -n vm-career-platform`.
  - **Undo:** Nothing changed. If you started it and want it off again: `az vm deallocate -g rg-career-platform -n vm-career-platform`.
  - **Result (2026-09-29):** `VM running`.

- [x] **Step 2: Confirm the laptop IP matches the NSG rule**
  - **Where:** laptop
  - **Run:** `curl -s https://api.ipify.org; echo`
  - **Why:** The `Allow-SSH-Laptop` rule only admits `<LAPTOP_IP_OLD>/32`.
  - **Check:** Prints `<LAPTOP_IP_OLD>`. If it doesn't, update the rule's source in the portal (NSG → Inbound security rules → Allow-SSH-Laptop → Source IP) to the new address.
  - **Undo:** If you edited the rule, set the source back to `<LAPTOP_IP_OLD>/32`.
  - **Result (2026-09-29):** `<LAPTOP_IP_OLD>`, which matches. No rule change needed.

- [x] **Step 3: SSH in once**
  - **Where:** laptop → VM
  - **Run:**
    ```bash
    ssh -i ~/.ssh/<ssh-key> azureuser@<VM_PUBLIC_IP> 'whoami; lsb_release -ds; df -h ~ | tail -1'
    ```
  - **Why:** Proves the key, user, and network path work. Also shows the OS and free disk space.
  - **Check:** Prints `azureuser`, `Ubuntu 24.04.x LTS`, and a free-space figure well over 1 GB. On first connect, accept the host key (the VM presents an ECDSA key).
  - **Undo:** Nothing on the VM. To forget the host key on the laptop: `ssh-keygen -R <VM_PUBLIC_IP>`.
  - **Result (2026-09-29):** `azureuser`, `Ubuntu 24.04.4 LTS`, 26G free on `/` (29G disk). The host key was trusted on first use: ECDSA `<HOST_KEY_FINGERPRINT>`. It has not yet been compared with the VM's own copy (portal → Run Command → `ssh-keygen -lf /etc/ssh/ssh_host_ecdsa_key.pub`).

## 2. Packages

### Task 2.1: Install git and sqlite3 ✅ Done 2026-09-29

- [x] **Step 1: Record what's already installed**
  - **Where:** VM
  - **Run:** `dpkg -l git sqlite3 2>/dev/null | grep ^ii`
  - **Why:** The undo step should only remove packages this migration added. Ubuntu cloud images usually ship `git` already.
  - **Check:** Write down which of `git` / `sqlite3` are listed.
  - **Undo:** Read-only.
  - **Result (2026-09-29):** `git 1:2.43.0-1ubuntu7.3` was already installed. `sqlite3` was not.

- [x] **Step 2: Install**
  - **Where:** VM
  - **Run:** `sudo apt-get update && sudo apt-get install -y git sqlite3`
  - **Why:** `git` for the clone. `sqlite3` to check the copied database.
  - **Check:** `git --version && sqlite3 --version` both print versions.
  - **Undo:** `sudo apt-get remove -y sqlite3` (git was preinstalled, so leave it). The `libsqlite3-0` upgrade is not rolled back. It's an Ubuntu security update that other system packages also use.
  - **Result (2026-09-29):** Both commands exited 0. apt added `sqlite3 3.45.1-1ubuntu2.8` and, as a dependency, upgraded `libsqlite3-0` to `3.45.1-1ubuntu2.8`. It reported 61 other packages as upgradable, which were left alone. `git version 2.43.0`, `sqlite3 3.45.1`.

## 3. Code

### Task 3.1: Create and push `uv.lock` (prerequisite the outline assumes) ✅ Done 2026-09-29

- [x] **Step 1: Install uv on the laptop**
  - **Where:** laptop
  - **Run:** `brew install uv`
  - **Why:** Needed to generate the lock file. uv isn't installed on the laptop today.
  - **Check:** `uv --version` prints a version.
  - **Undo:** `brew uninstall uv`
  - **Result (2026-09-29):** `uv 0.12.19 (Homebrew 2026-09-24 aarch64-apple-darwin)`.

- [x] **Step 2: Generate the lock**
  - **Where:** laptop, in `/Users/jacksondorr/career-platform`
  - **Run:** `uv lock`
  - **Why:** `uv sync --locked` on the VM needs a committed `uv.lock` so it installs exactly these versions. The lock is cross-platform, so a macOS-generated lock works on Linux.
  - **Check:** `uv.lock` exists, and `uv lock --check` exits 0. Then `uv sync --locked --extra test && uv run pytest` passes, so the locked versions are known to work. (This rebuilds the laptop `.venv` with uv. That's harmless.)
  - **Undo:** `rm uv.lock` (plus `rm -rf .venv && python3 -m venv .venv && .venv/bin/pip install -e ".[test]"` if you want the old venv back).
  - **⚠ Side effect:** `pytest` overwrites `data/public-profile.json`, because the tests don't isolate `SNAPSHOT_PATH` (`tests/test_web.py` saves a snapshot through `app.state.snapshot_store`). **Before** running the tests, back the file up (`cp data/public-profile.json /tmp/`). **Afterwards**, restore it, or rebuild it from the real DB with `uv run python -m app.snapshot`.
  - **Result (2026-09-29):** `uv lock` resolved 37 packages (`requires-python = ">=3.11"`), and `uv lock --check` exited 0. `uv sync --locked --extra test` exited 0; it moved the laptop venv to the locked versions, e.g. uvicorn 0.53.0 → 0.54.0. `uv run pytest` gave 11 passed, with 1 warning (a Starlette deprecation for `httpx` in the test client). The test run overwrote the local snapshot. It was rebuilt with `uv run python -m app.snapshot`, and its diff is back to exactly 90+/9−, matching the start of the session. The real DB was untouched (mtime still Sep 22).

- [x] **Step 3: Commit only the lock and push**
  - **Where:** laptop
  - **Run:**
    ```bash
    git add uv.lock
    git commit -m "Add uv lock file for reproducible deploys"
    git push origin main
    ```
  - **Why:** The VM clones from GitHub. Leave `data/public-profile.json` unstaged (Review Focus 5).
  - **Check:** `git show --stat HEAD` lists only `uv.lock`. `git status` shows `main` in sync with `origin/main`.
  - **Undo:** `git revert HEAD && git push origin main`
  - **Result (2026-09-29):** Commit `1e5ee06` contains only `uv.lock` (956 lines). Pushed after Jackson approved: `b83003f..1e5ee06  main -> main`. `main` is in sync with `origin/main`.

### Task 3.2: Clone on the VM ✅ Done 2026-09-29

- [x] **Step 1: Clone**
  - **Where:** VM
  - **Run:** `cd ~ && git clone https://github.com/jacksonddorr-dev/career-platform.git`
  - **Why:** Gets the code, now including `uv.lock`.
  - **Check:** `cd ~/career-platform && git log -1 --oneline` matches laptop `git log -1 --oneline`, and `ls uv.lock` succeeds.
  - **Undo:** `rm -rf ~/career-platform`
  - **Result (2026-09-29):** `~/career-platform` didn't exist beforehand. The clone's HEAD is `1e5ee06`, matching the laptop. `uv.lock` is present (195643 bytes, the same size as on the laptop).

## 4. Python

### Task 4.1: Install uv and the locked environment ✅ Done 2026-09-29

- [x] **Step 1: Install uv**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.local/bin/env
    ```
  - **Why:** uv manages the Python version and the virtualenv.
  - **Check:** `uv --version` prints a version, and `which uv` is `/home/azureuser/.local/bin/uv`.
  - **Undo:** `rm -f ~/.local/bin/uv ~/.local/bin/uvx ~/.local/bin/env ~/.local/bin/env.fish && rm -rf ~/.local/share/uv ~/.cache/uv`, then delete the `. "$HOME/.local/bin/env"` line from `~/.bashrc` (line 119) and `~/.profile` (line 29).
  - **Result (2026-09-29):** Run early, while the push in Task 3.1 is pending, because it doesn't need the clone. The installer exited 0. `uv 0.12.21 (x86_64-unknown-linux-gnu)` is at `/home/azureuser/.local/bin/uv`, and `~/.local/bin` was empty beforehand. The installer added the PATH line to `~/.bashrc:119` and `~/.profile:29`.

- [x] **Step 2: Sync from the lock**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `uv sync --locked`
  - **Why:** Creates `.venv` with exactly the locked runtime dependencies. `--locked` fails instead of silently re-resolving if the lock and `pyproject.toml` disagree.
  - **Check:** Exits 0. `.venv/bin/python -c "import app.main"` runs silently. It may print an Alembic/DB warning since there's no data yet, but it must not raise `ImportError`.
  - **Undo:** `rm -rf ~/career-platform/.venv`
  - **Result (2026-09-29):** Exited 0. uv used the system `CPython 3.12.3` at `/usr/bin/python3` (no Python download), created `.venv`, and installed 28 packages (runtime only, no test extras). `import app.main` printed `import ok` with no warnings. No `.db` file was created, which is expected before the Data section.

## 5. Config

### Task 5.1: Create `.env` ✅ Done 2026-09-29

- [x] **Step 1: Copy the template**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `cp .env.example .env && chmod 600 .env`
  - **Why:** `app/config.py` reads `.env`. `chmod 600` keeps the secrets readable only by `azureuser`.
  - **Check:** `ls -l .env` shows `-rw-------`.
  - **Undo:** `rm .env`
  - **Result (2026-09-29):** No `.env` existed beforehand. It now shows `-rw------- azureuser azureuser`, and `git status` on the VM is clean because `.env` is gitignored.

- [x] **Step 2: Replace the placeholders**
  - **Where:** VM
  - **Run:**
    ```bash
    sed -i "s/^SESSION_SECRET=.*/SESSION_SECRET=$(openssl rand -hex 32)/" .env
    sed -i "s/^APP_ENV=.*/APP_ENV=production/" .env
    nano .env   # set ADMIN_PASSWORD to a real value
    ```
    Leave `DATABASE_URL=sqlite:///./career_platform.db` and `SITE_URL=http://127.0.0.1:8000` as they are (the browser check goes through a tunnel to that address).
  - **Why:** The placeholder `SESSION_SECRET` would let anyone forge admin session cookies. Note that admin login checks the `admin_users` table in the copied DB. `ADMIN_PASSWORD` only matters for `app.seed`, which we don't run, but it shouldn't sit on disk as a placeholder.
  - **Check:** `grep -c replace- .env` prints `0`.
  - **Undo:** `cp .env.example .env` (back to placeholders) or `rm .env`.
  - **Result (2026-09-29, partial):** `SESSION_SECRET` is set to 64 hex characters from `openssl rand -hex 32` (the value was never printed). `APP_ENV=production` (`app_env` isn't read anywhere in `app/` besides config, so behavior doesn't change). `DATABASE_URL` and `SITE_URL` were left unchanged. `grep -c replace- .env` → `1`, which is only `ADMIN_PASSWORD`. **Jackson sets it** so the value is never shown to Claude. In a normal terminal, run: `ssh -t -i ~/.ssh/<ssh-key> azureuser@<VM_PUBLIC_IP> 'nano ~/career-platform/.env'`. Avoid spaces, `#`, and quotes in the value, because dotenv parsing treats ` #` as the start of a comment.
  - **Result (2026-09-29, final):** The nano edit never saved; nano stayed open (pid 2378) and `.env` was unchanged. Jackson switched to a no-editor command instead:
    ```
    ssh -t -i ~/.ssh/<ssh-key> azureuser@<VM_PUBLIC_IP> 'read -rsp "Admin password: " P; echo; P="$P" python3 -c "import os,re,pathlib; f=pathlib.Path.home()/\"career-platform/.env\"; f.write_text(re.sub(r\"(?m)^ADMIN_PASSWORD=.*\", lambda m: \"ADMIN_PASSWORD=\"+os.environ[\"P\"], f.read_text()))"'
    ```
    `.env` was written at 21:47:22 UTC and is still `-rw-------`. `grep -c replace- .env` → `0`. `ADMIN_PASSWORD` is set, with no space, `#`, or quote. `SESSION_SECRET` is 64 characters. The file has all 8 keys.
  - **⚠ Leftover:** When nano closed without a clean save, it wrote `~/career-platform/.env.save` (266 bytes, `-rw-------`). It had the same keys and SESSION_SECRET, but a *different* ADMIN_PASSWORD, and **it isn't gitignored**, so it showed as `??` in `git status`. **Deleted 2026-09-29 with Jackson's OK.** After that, `git status` on the VM was clean. Lesson: if nano won't save, quit with Ctrl-X then N. Don't close the terminal while nano is open.

## 6. Data

### Task 6.1: Copy the SQLite database from the laptop ✅ Done 2026-09-29

- [x] **Step 1: Take a consistent snapshot on the laptop**
  - **Where:** laptop, in `/Users/jacksondorr/career-platform`
  - **Run:**
    ```bash
    pgrep -fl "uvicorn app.main" && echo "STOP local uvicorn first"
    sqlite3 career_platform.db ".backup /tmp/career_platform.db"
    sqlite3 /tmp/career_platform.db "PRAGMA integrity_check; SELECT version_num FROM alembic_version; SELECT full_name FROM profiles;"
    shasum -a 256 /tmp/career_platform.db
    ```
  - **Why:** `.backup` produces a consistent copy even if something has the DB open (Review Focus 3).
  - **Check:** `ok`, `0001_initial`, and your name. Write down the SHA-256.
  - **Undo:** `rm /tmp/career_platform.db`. The original DB is untouched.
  - **Result (2026-09-29):** No local uvicorn and no `-wal`/`-journal` files. The backup was written to the session scratchpad instead of `/tmp` (same commands, different path). `integrity_check` → `ok`, `0001_initial`, `Ada Analyst`. SHA-256 `521c3f231bde4ea58c2c8a7f37995aaa520876dbe3ebd89211bba60dfc098b57` (65536 bytes). Row counts: achievements=0 admin_users=1 alembic_version=1 credentials=1 education=1 experiences=1 profiles=1 project_highlights=0 projects=1 skill_categories=1 skills=1. The laptop DB's mtime is still Sep 22 15:03.

- [x] **Step 2: scp it to the VM**
  - **Where:** laptop → VM
  - **Run:**
    ```bash
    scp -i ~/.ssh/<ssh-key> /tmp/career_platform.db \
      azureuser@<VM_PUBLIC_IP>:/home/azureuser/career-platform/career_platform.db
    ```
  - **Why:** The DB is gitignored, so the clone doesn't include it.
  - **Check:** On the VM, `sha256sum ~/career-platform/career_platform.db` matches step 1.
  - **Undo:** On the VM, `rm ~/career-platform/career_platform.db`.
  - **Result (2026-09-29):** No DB existed on the VM beforehand. `scp` exited 0, and the VM's `sha256sum` matches exactly (`521c3f23…c098b57`). It arrived as `-rw-r--r--`. Because the DB holds the admin password hash, it was tightened with `chmod 600 career_platform.db` (an addition to the plan).

- [x] **Step 3: Check it on the VM**
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    sqlite3 career_platform.db "PRAGMA integrity_check; SELECT full_name FROM profiles; SELECT (SELECT count(*) FROM experiences), (SELECT count(*) FROM projects), (SELECT count(*) FROM skills);"
    .venv/bin/alembic current
    ```
  - **Why:** Confirms the schema is at head, so no migration is needed. (Do **not** run `app.seed`, since it's for empty databases only.)
  - **Check:** `ok`, your name, the same counts as on the laptop (currently `1|1|1`), and `0001_initial (head)`.
  - **Undo:** Read-only.
  - **Result (2026-09-29):** `ok`, `Ada Analyst`. All 11 table counts are identical to the laptop. `alembic current` → `0001_initial (head)`, so no migration is needed and `app.seed` was not run. The checksum is unchanged after the checks, and no `-journal`/`-wal` file was left behind.

## 7. Processes

### Task 7.1: Start uvicorn ✅ Done 2026-09-29 (on `0.0.0.0`, changed from the plan)

- [x] **Step 1: Start in the background**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      > ~/uvicorn.log 2>&1 < /dev/null & echo $! > ~/uvicorn.pid
    ```
  - **Why:** Serves the app. Running from `~/career-platform` makes the relative DB and snapshot paths resolve correctly (Review Focus 4). Binding to `127.0.0.1` keeps it off the internet.
  - **Check:** `ps -p $(cat ~/uvicorn.pid)` shows the process. `tail ~/uvicorn.log` shows `Uvicorn running on http://127.0.0.1:8000` and no traceback. `ls ~/career-platform/*.db` shows only `career_platform.db`.
  - **Undo:** `kill $(cat ~/uvicorn.pid) && rm ~/uvicorn.pid`
  - **⚠ Command fix:** Keep `cd` on its own line. Writing `cd … && nohup … &` puts the *whole* `&&` chain in the background, so `$!` is a wrapper bash, not uvicorn. The PID file is then wrong, and when run over `ssh "…"` the session hangs because the wrapper holds stdout. `< /dev/null` also keeps SSH from waiting on stdin.
  - **Result (2026-09-29):** Jackson asked for all addresses on port 8000 instead of `127.0.0.1`. The first start used the `&&` form, which saved the wrapper PID 3304 while uvicorn was 3306, and the SSH session hung. uvicorn 3306 was stopped and restarted with the command above: PID 3381 (parent 1, so fully detached), and `~/uvicorn.pid` = 3381. The log shows `Uvicorn running on http://0.0.0.0:8000` with no traceback. The only DB is `career_platform.db`. `/api/v1/health` → `{"status":"ok","service":"career-platform"}` 200 on both 127.0.0.1 and the VM's private 10.x IP. `ss -ltnp`: `0.0.0.0:8000 uvicorn pid=3381`, alongside sshd on `0.0.0.0:22`/`[::]:22` and systemd-resolved on 127.0.0.53/54:53. No IPv6 listener for 8000.
  - **Restart (2026-09-29, ~22:44 UTC, at Jackson's request):** `kill $(cat ~/uvicorn.pid)` stopped 3381 cleanly (it had been up 29 min), then the start command above ran again. New PID **14981** (parent 1), and the PID file matches. Only one uvicorn process is running (a `pgrep -c` count of 2 included its own `bash -c`). The log is clean, and health is `200` on 127.0.0.1 and the private IP. `ss -ltnp`: `0.0.0.0:8000 uvicorn pid=14981`. Nothing in Azure was changed. Unrelated: Ubuntu **unattended-upgrades** ran at 22:14 UTC and restarted `ssh` and `systemd-resolved` (new PIDs 12296/12292) without a reboot (uptime since 21:14). uvicorn wasn't affected.

## 8. Verify

### Task 8.1: The site answers on the VM and shows your data ✅ Done 2026-09-29

- [x] **Step 1: Health check**
  - **Where:** VM
  - **Run:** `curl -s -w '\n%{http_code}\n' http://127.0.0.1:8000/api/v1/health`
  - **Why:** Proves the app is up and can reach its DB.
  - **Check:** Status `200`.
  - **Undo:** Read-only.
  - **Result (2026-09-29):** `{"status":"ok","service":"career-platform"}` → `200`.

- [x] **Step 2: Your data is on the page**
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    NAME=$(sqlite3 career_platform.db "SELECT full_name FROM profiles LIMIT 1")
    curl -s http://127.0.0.1:8000/ | grep -c "$NAME"
    for p in /about /experience /projects /skills /education /contact /resume.pdf; do
      printf '%s %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000$p)"; done
    ```
  - **Why:** A 200 alone could be the empty-DB or snapshot fallback. Matching the migrated profile name proves it's your data.
  - **Check:** The count is ≥ 1, and every path is `200`. `grep "snapshot fallback" ~/uvicorn.log` finds nothing.
  - **Undo:** Read-only. (The first successful `/` request rewrites `data/public-profile.json` on the VM. That's expected.)
  - **Result (2026-09-29):** The name from the DB is `Ada Analyst`, with 4 matches on `/`. All 8 paths return `200`: the 7 HTML pages are 1.8–2.1 KB each, and `/resume.pdf` is `application/pdf`, 1249 bytes, starting `%PDF-`. The log has 0 `snapshot fallback` lines and 0 tracebacks. As expected, the VM's `data/public-profile.json` was rewritten from the real DB (`"full_name": "Ada Analyst"`, and it shows `M` in `git status`).

- [x] **Step 3: Look at it in a laptop browser through a tunnel**
  - **Where:** laptop
  - **Run:** `ssh -i ~/.ssh/<ssh-key> -N -L 8000:127.0.0.1:8000 azureuser@<VM_PUBLIC_IP>`, then open `http://127.0.0.1:8000`. Stop any local uvicorn first so port 8000 is free.
  - **Why:** Lets you see it yourself without opening port 8000 in the NSG.
  - **Check:** Your profile, experience, and projects render, and `/admin` login works with your existing admin credentials.
  - **⚠ Plan correction:** The app has no login page. `GET /admin` returns `401` until a `session` cookie exists, and login is `POST /api/v1/auth/login` (form fields `username` and `password`), so it can't be done from the browser address bar. Check it with curl instead, through the tunnel (the password prompt is hidden):
    ```
    read -rsp "Admin password: " PW; echo; curl -s -c /tmp/cj -d "username=admin" --data-urlencode "password=$PW" http://127.0.0.1:8000/api/v1/auth/login; echo; curl -s -b /tmp/cj http://127.0.0.1:8000/admin; echo; rm -f /tmp/cj; unset PW
    ```
    Success looks like `{"authenticated":true,"username":"admin"}` followed by `Signed in as admin`. This checks the password hash in the **migrated DB** (whatever the laptop DB was seeded with), not `ADMIN_PASSWORD` in the VM's `.env`.
  - **Result (2026-09-29):** Claude started the tunnel in the background (laptop `127.0.0.1:8000` and `[::1]:8000` → VM). Through the tunnel: health `200`, title `Ada Analyst · Career Profile`, `/admin` → `401` without a session. **Jackson confirmed the site loads in the browser and the admin login worked.** The tunnel was then closed: laptop port 8000 is free again. uvicorn on the VM kept running (pid 3381), and health is still `200`.
  - **Undo:** Ctrl-C the tunnel.

## 9. Content: replace the seeded demo profile with Jackson's resume (added 2026-09-30)

Source: `Current_resume.pdf`. Jackson approved the field-by-field mapping on 2026-09-30. The script is `load_resume.py`, and the pre-change backup is `career_platform.pre-resume.db`. Both are kept in the plan's git-ignored workspace, `.superpowers/sdd/2026-09-24-azure-vm-migration/`.

### Task 9.1: Update the laptop DB ✅ Done 2026-09-30

- [x] **Step 1: Back up**
  - **Where:** laptop · **Run:** `sqlite3 career_platform.db ".backup <workspace>/career_platform.pre-resume.db"`
  - **Check:** `integrity_check` → `ok`, profile `Ada Analyst`, backup SHA-256 `521c3f23…`. That's byte-identical to the Section 6 copy, so the laptop DB hadn't changed since then.
  - **Undo:** n/a
- [x] **Step 2: Dry run on a scratch copy**
  - **Run:** `DATABASE_URL=sqlite:///<scratch>/dryrun.db uv run python load_resume.py`
  - **Check / Result:** profiles=1 experiences=3 achievements=10 projects=0 project_highlights=0 skill_categories=3 skills=21 education=1 credentials=0 admin_users=1. `integrity_check` → `ok`, and `foreign_key_check` is clean.
- [x] **Step 3: Apply to the laptop DB**
  - **Run:** `uv run python load_resume.py` (one transaction, using the app's own models)
  - **What changed:**
    - The profile row was updated in place: Jackson Dorr; headline "Information Systems & Business Analytics student at Loyola Marymount University"; the resume summary; Los Angeles, CA; <EMAIL>; LinkedIn URL. The phone number was deliberately left out.
    - Experience: 3 jobs (Spotlight Manager and Programming Team at Mane Entertainment, Membership Associate at Sonoma County YMCA) with 10 bullets as achievements.
    - Education: LMU, BBA, Information Systems & Business Analytics, ending 2027-05-01. Dean's List, activities, and coursework are in `honors`.
    - Skills: Microsoft Office (3), Technology (9), Professional (9, "Other" on the resume).
    - Removed: the demo project "Customer Health Signals" (the resume has no projects) and the fake credential "Data Analytics Certificate".
  - **Check / Result:** Counts and every content column are identical to the dry run. The admin user is unchanged (hash compared), `integrity_check` → `ok`, and no `-journal` file was left.
  - **Undo:** `sqlite3 career_platform.db ".restore <workspace>/career_platform.pre-resume.db"`
- [x] **Step 4: Render check (laptop, FastAPI TestClient, no server)**
  - **Result:** `/`, `/about`, `/experience`, `/skills`, `/education`, `/projects`, `/contact` → 200 with Jackson's content, and none of 6 demo strings remain. `/projects` shows "No published projects yet." `/resume.pdf` → 200, a valid PDF containing "Jackson Dorr". The location is shown on `/about` (the home page never shows it). `data/public-profile.json` was rebuilt as a side effect and now shows Jackson Dorr, with no demo strings.

### Task 9.2: Copy to the VM ✅ Done 2026-09-30

- [x] **Step 1: Restore SSH access**
  - **Where:** portal/Azure (Jackson's call)
  - **Why:** The laptop IP is now `<LAPTOP_IP>`. `Allow-SSH-Laptop` still allows only `<LAPTOP_IP_OLD>/32`, so SSH times out.
  - **Undo:** Set the source back.
  - **Result (2026-09-30):** At Jackson's request: `az network nsg rule update -g rg-career-platform --nsg-name vm-career-platform-nsg -n Allow-SSH-Laptop --source-address-prefixes <LAPTOP_IP>/32` → `Succeeded`. Only the source changed (was `<LAPTOP_IP_OLD>/32`); port 22, Allow, priority 300, and TCP are unchanged. SSH works again. The VM has been up 23 min, and uvicorn isn't running. `Temp-HTTP-8000` was left as is.
- [x] **Step 2: Repeat Section 6, then start uvicorn (Section 7)**
  - **Details:** Back up the VM's current DB first (`sqlite3 ~/career-platform/career_platform.db ".backup ~/career_platform.pre-resume.db"`), then run Tasks 6.1 → 7.1 → 8.1 with the new laptop DB. In the Verify step, look for `Jackson Dorr` instead of `Ada Analyst`.
  - **Note:** uvicorn isn't running, because the VM was deallocated and started again on 2026-09-30. The NSG now also has **`Temp-HTTP-8000` (port 8000 from `*`)**, which Claude didn't create. Once uvicorn starts, the site and the admin login are reachable over plain HTTP from the internet.
  - **Result (2026-09-30):**
    - Laptop `.backup` → `integrity_check` ok, `Jackson Dorr`, SHA-256 `928e22dde403ccbf17532816689e43c3ec58032a6c208eed2a2c60a2ff9292c2`.
    - The VM's live DB was still `521c3f23…` (unchanged since Section 6). It was backed up to `~/career_platform.pre-resume.db` (`-rw-------`, integrity ok, `Ada Analyst`).
    - Before the swap: 0 processes named uvicorn and 0 listeners on :8000. Two earlier checks falsely reported uvicorn running because `pgrep -f`/`grep` matched the SSH command's own text. **Use `pgrep -x uvicorn` or `ss -ltnH "sport = :8000"` instead.**
    - `scp` to `career_platform.db.new` gave a matching SHA-256; then `chmod 600` and `mv` over `career_platform.db`. On the VM: integrity ok, FK check clean, counts identical to Task 9.1, `alembic current` → `0001_initial (head)`.
    - Started uvicorn with the Task 7.1 command: pid **1727**, parent 1, listening on `0.0.0.0:8000`, clean log.
    - Verify on the VM: health 200; `/` Jackson Dorr, `/about` Los Angeles CA, `/experience`, `/skills`, `/education`, `/projects` ("No published projects yet."), `/contact` all 200 with the expected text and none of 5 demo strings. `/resume.pdf` is a valid PDF containing "Jackson Dorr". 0 fallback or traceback lines. The VM snapshot was rebuilt as Jackson Dorr.
    - **From the laptop over the internet:** `http://<VM_PUBLIC_IP>:8000/` → 200, `<title>Jackson Dorr · Career Profile</title>` (reachable because of `Temp-HTTP-8000`).
  - **Undo:** `kill $(cat ~/uvicorn.pid)`, then `cp ~/career_platform.pre-resume.db ~/career-platform/career_platform.db`, then start uvicorn again.

### Full rollback (reverse order)

Stop uvicorn (7) → `rm -rf ~/career-platform ~/uvicorn.log` on the VM (removes 3.2, 4.2, 5, 6) → uninstall uv on the VM (4.1) → remove packages you added (2) → optionally `git revert` the lock commit (3.1). The laptop's database and code are never modified by this plan, so the laptop stays the working fallback throughout.
