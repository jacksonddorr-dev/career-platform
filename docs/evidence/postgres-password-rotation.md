# Postgres password rotation — Railway

Date: **2026-10-25**. Railway project `prolific-enthusiasm`, environment `production`. Services: `career-platform` (web) and `Postgres`.

Deployment times come from `railway deployment list --json`. My own actions are timed from the Claude Code session log. No password appears in this file.

## Timeline

| Time (PDT) | Who | What happened | Evidence |
|---|---|---|---|
| 13:47:05 (20:47:05Z) | Me | First password **Regenerate** on the Postgres service. Railway redeployed Postgres (`a26d0bff`) and `career-platform` (`cb456bd7`, reason `redeploy`) together, half a second apart. Own words: This wa my initial regeneration and rotation of the postgress password by following the Railway Security Disclosure | Deployment list |
| 13:50:58 | Me | Asked Claude Code to redeploy every service that references the Postgres variables. Own words: Initial redeployment although not the final| Session log |
| 13:51:47 (20:51:47Z) | Claude Code | `railway redeploy` on `career-platform` → `a46a5e88` **FAILED** at build: Railpack said "No start command detected". This build skipped the cache. The live deployment was not affected. Own words: through the initial redpeployment command I recieved a warning stating "No start command detected."| Build log |
| 13:54:09 (20:54:09Z) | Claude Code | Redeployed the live image again with the current variables through the Railway API (`deploymentRedeploy`, `usePreviousImageTag: true`). This skipped the failing build → `6042b0f7` **SUCCESS**. | Deployment list, site returns 200 |
| 14:12:42 | Me | Pasted the full `DATABASE_URL`, including the password, into a `railway connect Postgres …` command. It failed (`connect` doesn't take a URL), but **the password was now exposed** in the session and its history. Own words: at this point I was attempting to troubleshoot and pasted the current password into the Claude Code session to try and find the problem. I later followed the Security disclosure steps once more and regenerated the password so the Claude session logs only copntain the old database password. No security risk.| Session log |
| 14:52:17 (21:52:25Z) | Me → Claude Code | Approved the Railpack fix. Commit `7a2113b` adds `railpack.json` with `deploy.startCommand: "sh scripts/start.sh"`. Pushed to `main` → `5344e39e` **SUCCESS**. Own words: I approved the "start command" fix.| Git log |
| 14:53:29 (21:53:29Z) | Claude Code | Uncached rebuild test → `2eb776be` **SUCCESS**. The build log shows "Using config file `railpack.json`" and `$ sh scripts/start.sh`. | Build log |
| ~15:02 | Claude Code | Removed the 1 line containing the password from Claude Code's prompt history (`~/.claude/history.jsonl`, 254 → 253 lines). `~/.zsh_history` and the zsh session history had no matches: `!` commands aren't written there. Own words: I removed any passwords from the shell. This was not needed as I later regenerated the password. | `grep -c` = 0 afterwards |
| 15:03:56 (22:03:56Z) | Me | Second password **Regenerate** (the rotation). Railway redeployed `Postgres` (`67c44ad8`) and `career-platform` (`7642eb16`) together. Own words: Since this private information was now in the Claude Code session logs I regenerated the password and redeployed.| Deployment list |
| 15:04:01 (22:04:01Z) | Railway | Postgres log: "database system is ready to accept connections". Every connection opened before this was closed. | Postgres log |
| 15:07:45 | Me → Claude Code | Own words: I asked Claude code to verify the rotation and these results are listed below. | Session log |

## Rotation check (2026-10-25, ~15:08 PDT)

| Check | Result |
|---|---|
| Current password differs from the exposed one | Yes |
| `PGPASSWORD`, `POSTGRES_PASSWORD` and the password inside Postgres's `DATABASE_URL` all match | Yes |
| `career-platform`'s `DATABASE_URL` uses the current password | Yes |
| Variables in either service that still contain the exposed password | 0 |
| The web app logged in to the database with the new password | Yes. `scripts/start.sh` runs `alembic upgrade head` under `set -e`, so it stops if that fails. uvicorn started, which means the migration logged in. |
| Pages are read from the database (no snapshot fallback) | Yes. `/`, `/about`, `/experience` and `/api/v1/health` return 200. The log has 0 "fallback" / "render failed" lines. |
| Failed logins in the Postgres log since the restart | None (no `authentication failed` or `FATAL` lines) |
| Other deployments or services that could still hold the old password | None. `career-platform` is the only app service, and its earlier deployments are `REMOVED`. |


## Other copies of the exposed password

- The Claude Code session transcript for this session still contains the exposed password. It wasn't edited. The password no longer works after the rotation.
