# Operate the VM Implementation Plan

> **Redacted for publishing:** the laptop's public IP is `<LAPTOP_IP>` and the SSH key file is `<ssh-key>`. The real values live in Azure and `~/.ssh`. The VM's public IP is left in because `jacksoncareer.me` resolves to it publicly anyway.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. While executing, tick each step and add a **Result** line under it.

## The VM (found 2026-10-01 with read-only `az` commands)

| What | Value |
|---|---|
| Subscription | Azure for Students (the only one) |
| Resource group | `RG-CAREER-PLATFORM` (North Central US) |
| VM | `vm-career-platform`, Standard_B2ats_v2 (2 vCPU, 1 GiB RAM), Ubuntu 24.04 LTS, running |
| Public IP | `52.159.85.45` (no DNS name) |
| SSH | `ssh -i ~/.ssh/<ssh-key> azureuser@52.159.85.45` (key login only, password login is off) |
| NSG `vm-career-platform-nsg` | `Allow-SSH-Laptop`: TCP 22 from `<LAPTOP_IP>/32`, priority 300 · `allow-HTTP-80`: TCP 80 from `*`, priority 310 |
| App on the VM | `/home/azureuser/career-platform`, venv `.venv`, DB `career_platform.db`, secrets in `.env` |
| How it runs today | Started by hand with `nohup .venv/bin/uvicorn … --host 0.0.0.0 --port 8000`, PID in `~/uvicorn.pid`, log in `~/uvicorn.log` |

**Goal:** Visitors open `http://52.159.85.45` (no port). The app starts at boot, restarts after a crash, and a single crash doesn't take the site down. Port 8000 is never reachable from the Internet, and the app never runs as root.

**Architecture:** Two pieces, both on the VM:

```
browser ──:80──▶ nginx ──▶ 127.0.0.1:8000 ──▶ uvicorn supervisor (azureuser, systemd service "career-platform")
                                                 ├── worker 1
                                                 └── worker 2
```

- **nginx** listens on port 80. Only root can open ports below 1024, so nginx's master process starts as root, opens port 80, and then hands requests to unprivileged `www-data` workers. It forwards every request to the app.
- **systemd** runs uvicorn as `azureuser`, bound to `127.0.0.1:8000` (loopback, so it can't be reached from outside the VM). Two workers mean that if one crashes, the other keeps serving while uvicorn replaces the dead one. If the whole uvicorn process dies, systemd starts it again after 3 seconds.

**Tech Stack:** Ubuntu 24.04, nginx (from apt), systemd, uvicorn 0.54 (already in `.venv`), FastAPI, SQLite.

**Spec:** Jackson's request in this session (2026-10-01). There's no separate spec file.

## Global Constraints

- Don't change any file tracked in the repo (on the laptop or the VM), and don't add tests. Editing `.env` on the VM is fine because it's gitignored.
- Use the existing code, `.venv`, and `career_platform.db` in `/home/azureuser/career-platform`.
- Service name: `career-platform`. It runs as `User=azureuser`.
- uvicorn binds to `127.0.0.1:8000` only. Port 8000 gets no NSG rule.
- Claude changes nothing in Azure. Jackson owns the port 80 rule.
- No crash tests and no reboot tests in this plan. Jackson runs those.

## Review Focus

1. **The hand-started uvicorn still holds port 8000.** If it's still running, the service fails with `address already in use`. If it's still on `0.0.0.0`, port 8000 also stays open on the VM. Task 2 Step 3 stops it and checks that nothing is listening before the service starts.
2. **Wrong working directory means an empty site.** `DATABASE_URL` and `SNAPSHOT_PATH` are relative paths. Without `WorkingDirectory=`, uvicorn would create a new, empty DB somewhere else. The unit file sets it, and Task 3 checks for your name on the page, not just a 200.
3. **nginx's default "Welcome to nginx" site.** It also claims `default_server` on port 80, so it would conflict with ours or answer instead of it. Task 1 removes its link, and Task 3 checks the page title.
4. **Canonical link points to `127.0.0.1:8000`.** `templates/base.html` builds `<link rel="canonical">` from `SITE_URL`. Task 2 Step 1 sets it to `http://52.159.85.45` in `.env`.
5. **Two workers share one SQLite file and one snapshot file.** Both workers rewrite `data/public-profile.json` on each page view, with a plain `write_text` that isn't atomic. Reads of that file only happen when the DB fails, so the risk is small, and fixing it would mean changing repo code (out of scope). It's noted here so nobody is surprised.

**About the port 80 rule:** the NSG *already* has `allow-HTTP-80` (TCP 80 from `*`, priority 310). Adding `Allow-HTTP-80` at priority 320 would duplicate it, and Azure may treat the two names as the same rule, since they differ only in letter case. Check the portal first (Task 0).

**Out of scope:** HTTPS and a domain name. The admin login still travels over plain HTTP, and its cookie has `secure=False`. Also out of scope: backups, crash and reboot tests.

---

## 0. Before you start

**What this does:** Confirms we can reach the VM and that Azure will let port 80 through. If either fails, nothing later will work, and the fix is in Azure, which is yours to change.

### Task 0.1: Preconditions ✅ Done 2026-10-01

- [x] **Step 1: Port 80 rule exists**
  - **Where:** Azure portal (Jackson), or the laptop (read-only check)
  - **Run:** `az network nsg rule list -g RG-CAREER-PLATFORM --nsg-name vm-career-platform-nsg -o table`
  - **Check:** A row allows TCP `80`, source `*`, `Allow`. Today `allow-HTTP-80` at 310 already does this. Jackson decides whether to keep it or replace it with `Allow-HTTP-80` at 320.
  - **Result (2026-10-01, laptop, read-only):** Two rules, unchanged since this morning: `Allow-SSH-Laptop` (300, TCP 22 from `<LAPTOP_IP>/32`) and `allow-HTTP-80` (310, TCP 80 from `*`, Allow). **Pass:** Azure already lets port 80 in. No `Allow-HTTP-80` at 320 exists yet, and none is needed for this plan. Adding it is Jackson's call. No `Temp-HTTP-8000` rule exists, so the NSG already blocks 8000.

- [x] **Step 2: SSH works**
  - **Where:** laptop
  - **Run:** `ssh -i ~/.ssh/<ssh-key> azureuser@52.159.85.45 'whoami; ss -ltnp | grep -E ":(80|8000) "'`
  - **Check:** Prints `azureuser`. This records what's listening now, which should be the hand-started uvicorn on `0.0.0.0:8000` and nothing on 80. If SSH times out, your laptop IP has probably changed (`curl -s https://api.ipify.org`). Ask Jackson to update `Allow-SSH-Laptop`.
  - **Result (2026-10-01, ~22:21 UTC):** The laptop's public IP is `<LAPTOP_IP>`, which matches `Allow-SSH-Laptop`. SSH connected without a prompt and printed `azureuser`. Listening: `0.0.0.0:8000` uvicorn pid **1241**, which matches `~/uvicorn.pid` and is the only `uvicorn` process (the one started by Run Command earlier today). **Nothing is on port 80**, because nginx isn't installed yet. The VM has been up 2 h 46 min. **Pass.** Nothing was changed on the VM or in Azure.

All later steps run **on the VM** in that SSH session, unless a step says laptop.

## 1. nginx: the front door on port 80

**What this does:** Installs nginx and tells it to forward everything on port 80 to `127.0.0.1:8000`. Visitors only ever talk to nginx. When the old uvicorn is still running, the site already works on port 80 at the end of this section.

### Task 1.1: Install and configure nginx ✅ Done 2026-10-01

**Files (VM, outside the repo):**
- Create: `/etc/nginx/sites-available/career-platform`
- Create link: `/etc/nginx/sites-enabled/career-platform`
- Remove link: `/etc/nginx/sites-enabled/default` (the file in `sites-available` stays)

- [x] **Step 1: Install nginx**
  - **Where:** VM
  - **Run:** `sudo apt-get update && sudo apt-get install -y nginx`
  - **Why:** apt installs nginx as a systemd service that's already enabled at boot.
  - **Check:** `systemctl is-enabled nginx` → `enabled`. `curl -s localhost | grep -o "<title>.*</title>"` → `Welcome to nginx!` (the default page, for now).
  - **Undo:** `sudo apt-get purge -y nginx nginx-common && sudo apt-get autoremove -y`
  - **Result (2026-10-01, ~22:22 UTC):** nginx wasn't installed before. `apt-get update` and `apt-get install -y nginx` both exited 0, and no services needed restarting. Installed `nginx/1.24.0 (Ubuntu)`. `is-enabled` → `enabled`, `is-active` → `active`. `localhost` → `Welcome to nginx!`, with only the `default` link in `sites-enabled`. **Pass.**

- [x] **Step 2: Write the site config**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<'EOF'
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    EOF
    ```
  - **Why:** `default_server` plus `server_name _` means "answer any request on port 80, whatever hostname or IP it used." `proxy_pass` forwards it to the app. The `X-Forwarded-*` headers pass along the visitor's real IP and scheme. uvicorn trusts them from `127.0.0.1` by default.
  - **Undo:** `sudo rm /etc/nginx/sites-available/career-platform`
  - **Result:** Written exactly as above. `cat` of the file on the VM matches the plan line for line.

- [x] **Step 3: Switch from the default site to ours**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
    sudo rm /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    ```
  - **Why:** nginx only loads what's linked in `sites-enabled`. Two `default_server`s on port 80 would make `nginx -t` fail (Review Focus 3). `nginx -t` checks the syntax before `reload` applies it, so a typo never takes nginx down.
  - **Check:** `nginx -t` prints `syntax is ok` and `test is successful`. `curl -s -o /dev/null -w "%{http_code}\n" localhost/api/v1/health` → `200`, served through nginx to the old uvicorn.
  - **Undo:** `sudo rm /etc/nginx/sites-enabled/career-platform && sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default && sudo systemctl reload nginx`
  - **Result (2026-10-01, ~22:23 UTC):** `sites-enabled` now holds only `career-platform → /etc/nginx/sites-available/career-platform`. `sites-available/default` is still there for the Undo. `nginx -t` → `syntax is ok` / `test is successful`, and reload exited 0. On the VM: `localhost/api/v1/health` → `200`, and `/` → `Jackson Dorr · Career Profile` (proxied to the hand-started uvicorn, pid 1241). Listening: nginx on `0.0.0.0:80` and `[::]:80`, uvicorn still on `0.0.0.0:8000`. nginx processes: master pid 2543 as `root` (needed to open port 80), workers 2687/2688 as `www-data`. **Extra check from the laptop over the Internet:** `http://52.159.85.45/` → `200`, title `Jackson Dorr · Career Profile`, and the access log shows the requests from `<LAPTOP_IP>`. **Pass.** The site is now public on port 80. Port 8000 still listens on all addresses until Section 2 swaps in the service, but the NSG blocks it from the Internet.

## 2. systemd: keep the app running

**What this does:** systemd is Ubuntu's process manager. It starts things at boot and restarts them when they die. A *unit file* describes one service. Ours runs uvicorn as `azureuser`, from the app directory, on loopback, with 2 workers. Then we swap the hand-started process for the service. The site is down for a few seconds during that swap.

### Task 2.1: Create and start the `career-platform` service ✅ Done 2026-10-01

**Files (VM):**
- Modify: `/home/azureuser/career-platform/.env` (gitignored, one line)
- Create: `/etc/systemd/system/career-platform.service`

- [x] **Step 1: Point `SITE_URL` at the public address**
  - **Where:** VM
  - **Run:** `cd ~/career-platform && cp .env ~/env.pre-operate && sed -i 's|^SITE_URL=.*|SITE_URL=http://52.159.85.45|' .env`
  - **Why:** It's used for the page's canonical link (Review Focus 4). The new value takes effect when the service starts in Step 4.
  - **Check:** `grep ^SITE_URL= .env` → `SITE_URL=http://52.159.85.45`. `ls -l .env` still shows `-rw-------`.
  - **Undo:** `cp ~/env.pre-operate ~/career-platform/.env`
  - **Result (2026-10-01, ~22:24 UTC):** Before: `SITE_URL=http://127.0.0.1:8000`. No `~/env.pre-operate` existed beforehand. It's now the backup (`-rw-------`, 264 bytes). After: `SITE_URL=http://52.159.85.45`, and `.env` is still `-rw-------` (262 bytes, 2 shorter, as expected for the shorter URL). The same 8 keys are present. **Pass.**

- [x] **Step 2: Write the unit file**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/systemd/system/career-platform.service > /dev/null <<'EOF'
    [Unit]
    Description=Career Platform (FastAPI via uvicorn)
    After=network.target

    [Service]
    User=azureuser
    Group=azureuser
    WorkingDirectory=/home/azureuser/career-platform
    ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
    Restart=always
    RestartSec=3

    [Install]
    WantedBy=multi-user.target
    EOF
    ```
  - **Why, line by line:**
    - `User`/`Group`: the app runs as `azureuser`, never as root.
    - `WorkingDirectory`: the relative DB path resolves to the real DB (Review Focus 2). uvicorn reads `.env` from here.
    - `--host 127.0.0.1`: port 8000 is reachable only from inside the VM.
    - `--workers 2`: one parent process watches 2 workers and replaces any that die. The VM has 2 vCPUs and 1 GiB RAM, so 2 is the right size.
    - `Restart=always` + `RestartSec=3`: if the parent dies, systemd starts it again after 3 seconds. 3 s keeps it under systemd's default limit of 5 starts in 10 s, so it won't give up during a short crash loop.
    - `WantedBy=multi-user.target`: start at normal boot once `enable` is run.
  - **Check:** `sudo systemd-analyze verify /etc/systemd/system/career-platform.service` prints nothing (no errors).
  - **Undo:** `sudo rm /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload`
  - **Result:** No unit file existed beforehand. It was written exactly as above, and the `cat` matches line for line. `systemd-analyze verify` printed nothing and exited 0. **Pass.**

- [x] **Step 3: Stop the hand-started uvicorn**
  - **Where:** VM
  - **Run:** `kill $(cat ~/uvicorn.pid)`, wait about 2 seconds, then run `ss -ltnH "sport = :8000"`
  - **Why:** It holds port 8000 (Review Focus 1). From here until Step 4 finishes, the site shows nginx's `502 Bad Gateway`.
  - **Check:** `ss` prints nothing, and `pgrep -x uvicorn` prints nothing. If something is still listening, find its PID with `ss -ltnp "sport = :8000"` and `kill` that. Don't use `pgrep -f`, which matches its own command line.
  - **Undo:** Restart it the old way: `cd ~/career-platform` on its own line, then `nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/uvicorn.log 2>&1 < /dev/null & echo $! > ~/uvicorn.pid`
  - **Result:** Steps 3 and 4 ran in one SSH call to keep the downtime short. The start was guarded: it would only run if :8000 was free. `~/uvicorn.pid` = 1241 = `azureuser … uvicorn app.main:app --host 0.0.0.0 --port 8000`. `kill` at 22:24:26 UTC. The port freed within the wait loop: `ss` empty, `pgrep -x uvicorn` empty. The old log ends with a clean shutdown (`Finished server process [1241]`). **Pass.**

- [x] **Step 4: Enable and start the service**
  - **Where:** VM
  - **Run:** `sudo systemctl daemon-reload && sudo systemctl enable --now career-platform`
  - **Why:** `daemon-reload` makes systemd read the new file. `enable` turns on start-at-boot. `--now` also starts it right away.
  - **Check:** `systemctl is-active career-platform` → `active`. `systemctl is-enabled career-platform` → `enabled`. `journalctl -u career-platform -b --no-pager | grep -c "Started server process"` → `2`, one line per worker.
  - **Undo:** `sudo systemctl disable --now career-platform`
  - **Result:** `enable --now` exited 0 and created the `multi-user.target.wants/career-platform.service` symlink. Started 22:24:27, and the first health `200` came at 22:24:28, so **the site was down about 2 seconds**. `is-active` → `active`, `is-enabled` → `enabled`. The journal shows `Uvicorn running on http://127.0.0.1:8000`, `Started parent process [2982]`, and `Started server process` ×**2** (workers 3005, 3006), both with `Application startup complete`. **Pass.**

- [x] **Step 5: Retire the old PID file and log**
  - **Where:** VM
  - **Run:** `mv ~/uvicorn.log ~/uvicorn.pre-service.log && rm ~/uvicorn.pid`
  - **Why:** They described the hand-started process. The app's logs now go to the systemd journal: `journalctl -u career-platform -f`.
  - **Undo:** `mv ~/uvicorn.pre-service.log ~/uvicorn.log`
  - **Result:** `mv` and `rm` exited 0. Only `~/uvicorn.pre-service.log` (1238 bytes) remains. Quick look ahead to Section 3: `ss` shows `127.0.0.1:8000` (parent 2982 + workers 3005/3006) and nginx on `0.0.0.0:80` and `[::]:80`. **No `0.0.0.0:8000` anymore.** The only DB is `career_platform.db`. From the laptop, `http://52.159.85.45/` → `Jackson Dorr · Career Profile`. **Pass.**

## 3. Verify

**What this does:** Checks each requirement from the place a visitor would see it. "Laptop" checks go over the Internet, the same path a visitor takes. "VM" checks show what's listening and who owns it. Record each result in the table below.

### Task 3.1: Check every requirement ✅ Step 1 done 2026-10-05 · Step 2 is Jackson's

- [x] **Step 1: Run the checks**

| # | Requirement | Where | Run | Pass when |
|---|---|---|---|---|
| 1 | Site at the bare IP | laptop | `curl -s -o /dev/null -w "%{http_code}\n" http://52.159.85.45/` | `200` |
| 2 | It's *our* site with *our* data | laptop | `curl -s http://52.159.85.45/ \| grep -o "<title>.*</title>"` | `Jackson Dorr · Career Profile` (not `Welcome to nginx!`) |
| 3 | Canonical link is public | laptop | `curl -s http://52.159.85.45/about \| grep -o 'rel="canonical"[^>]*'` | `href="http://52.159.85.45/about"` |
| 4 | All pages work | laptop | `for p in / /about /experience /skills /education /projects /contact /resume.pdf /api/v1/health; do printf "%s " $p; curl -s -o /dev/null -w "%{http_code}\n" http://52.159.85.45$p; done` | every line `200` |
| 5 | Port 8000 closed to the Internet | laptop | `curl -s --max-time 5 http://52.159.85.45:8000/; echo "exit $?"` | `exit 28` (timeout, the NSG drops it) or `exit 7` (refused). Anything but a page. |
| 6 | 8000 only on loopback, 80 by nginx | VM | `sudo ss -ltnp \| grep -E ":(80\|8000) "` | `127.0.0.1:8000` (uvicorn) and `0.0.0.0:80` / `[::]:80` (nginx). No `0.0.0.0:8000`. |
| 7 | App not running as root | VM | `ps -o user=,pid=,ppid=,args= $(cat /sys/fs/cgroup/system.slice/career-platform.service/cgroup.procs)` | every line starts with `azureuser`. A parent plus 2 workers. |
| 8 | Starts at boot | VM | `systemctl is-enabled career-platform nginx` | `enabled` twice |
| 9 | Restart policy in place | VM | `systemctl show career-platform -p Restart -p RestartUSec -p User -p WorkingDirectory` | `Restart=always`, `RestartUSec=3s`, `User=azureuser`, `WorkingDirectory=/home/azureuser/career-platform` |
| 10 | Real DB, no stray empty one | VM | `ls ~/career-platform/*.db; journalctl -u career-platform -b --no-pager \| grep -ciE "traceback\|snapshot fallback"` | only `career_platform.db`; count `0` |

  - **Undo:** All read-only.
  - **Result (2026-10-05, ~20:16 UTC; laptop IP `<LAPTOP_IP>`):** **All 10 pass.**

    | # | What it showed | |
    |---|---|---|
    | 1 | `200` | ✅ |
    | 2 | `<title>Jackson Dorr · Career Profile</title>` | ✅ |
    | 3 | `rel="canonical" href="http://52.159.85.45/about"` | ✅ |
    | 4 | All 9 paths (`/`, `/about`, `/experience`, `/skills`, `/education`, `/projects`, `/contact`, `/resume.pdf`, `/api/v1/health`) → `200` | ✅ |
    | 5 | `exit 28` after 5 s: the NSG drops the packet, so no page | ✅ |
    | 6 | `127.0.0.1:8000` (uvicorn 665 + workers 862/864), nginx on `0.0.0.0:80` and `[::]:80` (747–749). No `0.0.0.0:8000`. | ✅ |
    | 7 | 4 processes, all `azureuser` (uid 1000), none root: parent 665 (ppid 1), workers 862 and 864, plus 861, Python's `multiprocessing.resource_tracker` helper. The plan expected 3. The 4th is a helper started by uvicorn's multi-worker mode, not a third worker. | ✅ |
    | 8 | `enabled` / `enabled` | ✅ |
    | 9 | `Restart=always`, `RestartUSec=3s`, `User=azureuser`, `WorkingDirectory=/home/azureuser/career-platform` | ✅ |
    | 10 | only `career_platform.db`; `0` tracebacks/fallbacks this boot | ✅ |

    **Starts at boot, seen in practice (not a test Claude ran):** `last -x` shows the VM was down from **2026-10-02 02:01 to 2026-10-05 20:04 UTC**. It booted at 20:04:25, and `career-platform` was active at **20:04:34**, 9 s later, with nobody starting it by hand (`NRestarts=0`). nginx came up too. Every PID above is new since the swap on 2026-10-01, which confirms systemd started them. Nothing was changed on the VM or in Azure.

- [x] **Step 2: Browser check (Jackson)**
  - **Where:** laptop browser
  - **Run:** open `http://52.159.85.45`
  - **Check:** Your resume loads with no `:8000` in the address bar.

## 4. Record

**What this is:** A snapshot of what the VM exposes, so anyone reading this later can see what's open and why without logging in. Taken **2026-10-08 00:43 UTC**. SSH was blocked because the laptop's IP had changed, so with Jackson's OK the commands ran through Azure Run Command (`az vm run-command invoke … RunShellScript`, which runs as root, so no `sudo`). Read-only. Nothing was changed on the VM or in the NSG.

### Listening ports (`ss -ltnp`, TCP)

| Address | Port | Program (PID) | Reachable from the Internet? | What it's for |
|---|---|---|---|---|
| `0.0.0.0`, `[::]` | 80 | nginx: master 754 (root) + workers 755/756 (`www-data`) | **Yes**, via `allow-HTTP-80` | The website's front door. Forwards to 127.0.0.1:8000. |
| `127.0.0.1` | 8000 | uvicorn 664 + workers 875/876 (`career-platform` service, `azureuser`) | No, loopback only, and the NSG has no rule for it | The app itself. Only nginx talks to it. |
| `0.0.0.0`, `[::]` | 22 | systemd (pid 1) | Only from `<LAPTOP_IP>/32`, via `Allow-SSH-Laptop` | SSH. On Ubuntu 24.04, `ssh.socket` makes systemd hold port 22 and start `sshd` for each connection, so `ss` shows systemd, not sshd. |
| `127.0.0.53%lo`, `127.0.0.54` | 53 | systemd-resolved (464) | No, loopback | The VM's own DNS cache. |

UDP (`ss -lunp`), for completeness: chronyd on `127.0.0.1:323` / `[::1]:323` (clock sync, loopback), systemd-resolved on `127.0.0.53`/`127.0.0.54:53` (loopback), and systemd-networkd on `172.16.0.4:68` (DHCP client, which gets the VM's private IP from Azure). The NSG has no UDP allow rule.

### IP addresses

| Kind | Address | Notes |
|---|---|---|
| Private | `172.16.0.4/24` on `eth0` | The VM's address inside its Azure virtual network. It's the only non-loopback address the VM itself sees. |
| Public | `52.159.85.45` (static, resource `vm-career-platform-ip`) | Azure translates it to the private IP at the network edge, which is why no `52.x` address appears in `ss` or `ip addr`. `jacksoncareer.me` and `www.jacksoncareer.me` point here (Cloudflare DNS, "DNS only", not proxied). |

### NSG inbound rules (`vm-career-platform-nsg`, attached to the VM's NIC)

Azure checks rules from the lowest priority number up. The first match wins.

| Priority | Name | Allows | Why it exists |
|---|---|---|---|
| 300 | `Allow-SSH-Laptop` | TCP 22 from `<LAPTOP_IP>/32` | Admin SSH from Jackson's laptop only, never from the whole Internet. It has to be updated whenever the laptop's IP changes, as it had on 2026-10-08. |
| 310 | `allow-HTTP-80` | TCP 80 from `*` | The public website (nginx). Added by Jackson. |
| 65000 | `AllowVnetInBound` | anything from inside the virtual network | Azure default. It can't be deleted. Nothing else runs in this VNet. |
| 65001 | `AllowAzureLoadBalancerInBound` | Azure's load-balancer probes | Azure default. Not used here. |
| 65500 | `DenyAllInBound` | nothing (deny) | Azure default. Everything not allowed above is dropped, **including port 8000**. That's why Section 3, row 5 timed out. |

## Full rollback (reverse order)

`sudo systemctl disable --now career-platform` → `sudo rm /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload` → `cp ~/env.pre-operate ~/career-platform/.env` → start uvicorn by hand (Task 2.1 Step 3 Undo) → restore the nginx default site (Task 1.1 Step 3 Undo) → optionally purge nginx (Task 1.1 Step 1 Undo). The repo, the venv, and the DB are never modified, so rollback can't lose data.