# Reviewed change through Railway: 503 on database failure

Written 2026-10-26 from the Claude Code session in which the change was made (2026-10-25 to 2026-10-26). Times are UTC.

## The change

Before, a failed database read served the last snapshot with **HTTP 200**, including its projects. On Railway that snapshot was the committed placeholder profile ("Cached Candidate"). After the change:

- A failed read keeps the profile from the snapshot, shows "Projects temporarily unavailable," lists no projects, and returns **503** on every public page.
- The next healthy request returns 200 with projects, without a restart.
- The placeholder snapshot is no longer committed. `scripts/start.sh` writes a real one from the database at every boot.

Code commit: **`4afc2ee`** "Return 503 with projects unavailable on DB failure; write snapshot at boot" (10 files, +107/−33). Pushed together with the docs commit `61ad97c`.

## 1. Tests first

New tests in `tests/test_web.py` and `tests/test_foundation.py`, run before the fix:

```
$ .venv/bin/pytest -q tests/test_web.py
FAILED test_database_failure_keeps_profile_hides_projects_and_returns_503[/]       assert 200 == 503
FAILED test_database_failure_keeps_profile_hides_projects_and_returns_503[/about]  assert 200 == 503
FAILED test_database_failure_keeps_profile_hides_projects_and_returns_503[/projects] assert 200 == 503
FAILED test_projects_return_after_database_recovers_without_restart                assert 200 == 503
4 failed, 5 passed

$ .venv/bin/pytest -q tests/test_foundation.py::test_start_script_writes_real_snapshot_after_migrating_without_blocking_boot
FAILED ... StopIteration      # no `python -m app.snapshot` line in start.sh yet
```

The healthy-page test first failed for a different reason (`no such table: profiles`): the in-memory test database gave each thread its own empty connection. The test fixture was fixed to share one connection (`StaticPool`) before the app code was changed.

## 2. Diff review (before committing)

The full diff of `app/main.py`, `app/templates/_parts.html`, `base.html`, `home.html`, and `tests/conftest.py` was shown in the session, and I read it before approving the commit. What to check in it:

- `current_content()` now separates a **failed read** (503, snapshot projects dropped) from a **healthy database with no published profile** (unchanged: snapshot, 200).
- Saving the snapshot moved outside the `try`, so a disk error can't be mistaken for a database failure.
- The templates treat `None` projects as "unavailable" and an empty list as "none published yet."
- The test fixture writes the snapshot to a temp file, so `pytest` no longer overwrites `data/public-profile.json`.

## 3. Local checks (before pushing)

| Check | Result |
|---|---|
| Full suite, `.venv/bin/pytest -q` | **31 passed, 2 skipped** (the 2 live-Postgres tests need `TEST_DATABASE_URL`) |
| `python -m compileall -q app` | OK |
| Committed snapshot untouched by tests | `data/public-profile.json` modification time unchanged across the run |
| Boot `scripts/start.sh` on a scratch SQLite DB with a published profile (port 8799) | health 200; snapshot written with the seeded name `Ada Analyst` |
| Same, with no published profile | health 200; log `No published profile is available`, then `start.sh: snapshot not written; continuing without one`; no snapshot file |

## 4. Commit, push, Railway deployment

- `4afc2ee` and `61ad97c` committed at 2026-10-25 23:54:44 UTC and pushed (`0a086f8..61ad97c main -> main`).
- Railway built deployment **`79ca6fd3-2d6a-4340-99e8-6fc2ebac0b0d`** for commit `61ad97c` (created 23:55:16 UTC) → **SUCCESS**.
- Its deploy log: `Wrote data/public-profile.json` and `Uvicorn running on http://0.0.0.0:8080`, with no errors.
- Railway only lists the last 20 deployments, so `79ca6fd3` no longer appears in `railway deployment list`. The ID was recorded at the time, in this session and in the live-check record in `TASKS.md`.

## 5. Observed at the domain

- Right after the deploy: `/`, `/about`, `/projects`, `/api/v1/health` → 200, title `Jackson Dorr · Career Profile`, no "Cached Candidate."
- **The new behavior, live (2026-10-26):** during a Postgres restart at 00:15:39–00:15:40 UTC, `https://jacksoncareer.me/` returned **503 with "Projects temporarily unavailable" and no project** 11 times, then 200 with the project back, while still on deployment `79ca6fd3`. Full record: the final section of `TASKS.md`.

## Recovery

If this change had been bad, the steps are in the README's "Rolling back a bad change":
- `git revert 4afc2ee` and push, or Railway's dashboard **Rollback** to the previous deployment (`e2e7d2ae`, commit `0a086f8`), followed by the revert.
- The change has no database migration and writes no data, so no data rollback would be needed.
- Rolling back brings back the old behavior, including the committed placeholder snapshot: the revert restores `data/public-profile.json`, and the previous deployment's image still contains it. During an outage the site would again show "Cached Candidate" with 200 until a page load refreshed the snapshot.

