# Project 1 gaps

From the repository audit on 2026-10-20 against the Project 1 requirements. Each line names the file or check that closes it.

## 1. Profile and project data

- [x] Add a clearly labeled "this website, in progress" project row in Railway Postgres — closes when `/projects` on https://jacksoncareer.me lists it
- [x] On DB failure, keep the profile visible, show "Projects temporarily unavailable," and return 503 instead of the snapshot with 200 — `app/main.py` `current_content()`
- [x] Stop the committed placeholder snapshot ("Cached Candidate") from being served on Railway — `data/public-profile.json` / `app/snapshot.py`

- [x] Replace the snapshot-fallback test with tests for 503 on failure, 200 when healthy, and recovery without restart — `tests/test_web.py`
- [x] Record a dated failure → 503 → recovery → 200 check against the deployed app — evidence file linked from `docs/project-1-submission.md`
- [x] Explain why SQLite was chosen as the initial engine — `docs/superpowers/specs/2026-09-15-career-platform-design.md` or README decisions section

## 2. Azure deployment

- [x] Run and record a controlled VM restart (site, DB read, and service up afterward) — `docs/superpowers/plans/2026-10-01-operate-the-vm.md` Result line — **closed, not run:** VM deleted 2026-10-13 per the instructor; existing restart evidence and the gap are recorded in that plan's section 5
- [x] Document the Azure HTTPS setup: certbot install, nginx 443 config, NSG 443 rule — Azure plan or `docs/how-this-site-is-secured.md` — **closed, partly documented:** NSG rule and certificate recorded in the addendum to that file; certbot, nginx 443 config, and renewal output weren't recorded and were lost with the VM
- [x] Confirm the VM is still running and serving — dated `az vm get-instance-view` / `curl http://52.159.85.45/` output — **closed:** checked 2026-10-26, the VM is deleted (`ResourceNotFound`, no response at `52.159.85.45`); recorded in the operate-the-VM plan's section 5

## 3. Domain and HTTPS

- [x] Make `www` a proxied Cloudflare record with a redirect rule to the bare domain — Cloudflare dashboard — done 2026-10-26 with the `cf` CLI; `docs/evidence/www-redirect.md`
- [x] Verify `http://www` and `https://www` both land on `https://jacksoncareer.me` with a valid certificate — dated `curl -I` output in evidence — `docs/evidence/www-redirect.md`
- [x] Fix the README's `www` row, which contradicts the 2026-10-13 DNS snapshot — `README.md` Domains and DNS
- [x] Record the final DNS records and their purposes after Zoho and the `www` change — `docs/evidence/` DNS file — `docs/evidence/dns-final.md`
- [x] Record the Railway certificate's hostname, issuer, validity, and renewal arrangement — `openssl s_client` output in `docs/how-this-site-is-secured.md`
- [x] Add real renewal-test output (`certbot renew --dry-run`, `systemctl list-timers`) — `docs/how-this-site-is-secured.md` — **closed, not possible:** those commands ran on the Azure VM, deleted 2026-10-13, and their output was never saved; the current arrangement (Railway renews at 30 days left, about 2026-12-10) and how to check it are in that file's Railway certificate addendum

## 4. Railway and PostgreSQL migration

- [x] Add the Railway spec, or explain why the plan stands in for it — `docs/superpowers/specs/`

  **Why the plan stands in for a spec (written 2026-10-26, after the migration).** No separate Railway spec was written during the lesson. `docs/superpowers/specs/` holds only the original 2026-09-15 design spec, and the plan says so itself: "No separate spec doc. This plan comes from the 2026-10-10 inspection recorded under *Starting state*." The spec content lives in `docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`:

  The plan was committed in `6c4ce35`, `e2fe8f4`, and `7cd922f` (2026-10-11 00:17–00:21 UTC). That's before the VM database backup (00:26 UTC), the data copy, and the DNS cutover, so it was written before the working deployment changed.

- [x] Commit the uncommitted Task 5 results — `docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`
- [x] Complete or annotate Task 5 Steps 1–3 and 6 (variables, source, first deploy, page/PDF parity check) — Railway plan — annotated 2026-10-26; Step 6 parity was never run and can't be now (VM deleted)
- [x] Record the cutover: time (UTC), deployed commit, DNS before and after, post-cutover checks — Railway plan Tasks 6–7 Record section — reconstructed 2026-10-26 from the Cloudflare audit log; deployed commit inferred (`7cd922f`); no checks were recorded on the day
- [x] Make one real change to project data and show it on both source and target, so seed data can't pass as a transfer — Railway plan plus a rendered-page comparison — **closed, by existing evidence:** the 2026-09-30 résumé change (replacing seeded "Ada Analyst") is on the VM data and identical on Railway; the gaps (no project row, no page comparison) are in the Railway plan's Step 5 annotation
- [x] Compare the rendered pages from source and target — Railway plan Step 6 output — **closed, not possible:** never run before the cutover, and the VM was deleted on 2026-10-13; see the Railway plan's Step 6 annotation
- [x] Write the Azure-vs-Railway responsibility comparison (OS, runtime, web entry, TLS, code, config, DB software, data, DNS) — README migration section — README "Azure to Railway: who manages what"
- [x] Write the rollback procedure, including data written after cutover — README rollback section (commit it) — README "Rolling back a bad change"; data steps untested and no backup exists yet

## 5. Reviewed change through Railway

- [x] Connect one reviewed commit SHA to its Railway deployment ID and the observed live change — evidence linked from `docs/project-1-submission.md` — `docs/evidence/reviewed-change.md` (`4afc2ee` → deployment `79ca6fd3` → live 503 check)
- [x] Record the diff review and local check done before pushing — the same evidence
- [x] Explain how to restore a previous version for code and for database changes — README rollback section — README "Rolling back a bad change" (data steps untested)

## 6. Zoho email

- [ ] Create the header analysis showing SPF, DKIM, and DMARC results — `docs/evidence/zoho-header-check.md`
- [ ] Add a line for the message sent before MX existed and what happened to it — `docs/evidence/ex06.md`
- [ ] Reply from Zoho webmail and confirm Gmail shows the custom sender — `docs/evidence/ex06.md` Replied row
- [ ] Replace both "_Check Gmail_" cells with confirmed delivery results — `docs/evidence/ex06.md`

## 7. GA4

- [ ] Record the action performed, the event observed (page_view and click), the date, and why the event is useful — `docs/evidence/ex06.md` §3 or README analytics section
- [ ] Explain the collection path from the browser to GA (consent → gtag → collect) and what Realtime/DebugView showed — README analytics section
- [ ] Confirm the outbound click relies on enhanced measurement, or add an explicit event — GA admin settings or `app/templates/base.html`

## 8. Engineering record

- [ ] Create the submission index with the repo URL, live URL, final SHA, and links to all evidence — `docs/project-1-submission.md`
- [ ] Commit the README changes — `README.md`
- [ ] Put what the site does and its live address at the top — `README.md`
- [ ] Add Azure and Railway architecture diagrams with locations, protocols, ports, and email and analytics paths — `README.md` or a linked diagrams file
- [ ] Add at least two decisions with alternatives and reasons (Railway migration, managed vs. self-hosted email) — `README.md`
- [ ] Add investigated failures, linking `docs/evidence/ex03.md` and `docs/evidence/ex05.md` and labeling ex05 as a deliberate lab — `README.md`
- [ ] Add remaining limitations — `README.md`
- [ ] Add a short reflection — `README.md`
- [ ] Add costs and credits, the Railway trial end date, a service inventory, and cleanup plans — `README.md`
- [ ] Link the original spec and all plans — `README.md` and `docs/project-1-submission.md`

---

## Record: live database failure → 503 → recovery → 200 (2026-10-26 UTC)

Evidence for the section 1 item "Record a dated failure → 503 → recovery → 200 check". It lives here until `docs/project-1-submission.md` exists, which should then link to this section. Times are UTC on 2026-10-26 (the evening of 2026-10-25 in PDT).

**Setup**
- Deployed app: Railway deployment `79ca6fd3` (commit `61ad97c`), which includes the 503 change from `4afc2ee`. Its boot log shows `Wrote data/public-profile.json`, so the snapshot came from the real database.
- Failure: I restarted only the Postgres service with `railway restart -s Postgres -y` (run by me at the Claude Code prompt). The app kept running.
- Probe: a Python script (kept outside the repo) requested `https://jacksoncareer.me/` about 10 times a second and `/api/v1/health` once a second, from 00:15:16 to 00:19:16. For each response it recorded the send time, the status, whether "Projects temporarily unavailable" was on the page, and whether "This Website (In Progress)" was listed.

**Postgres log**

```
00:15:39.634  LOG:  shutting down
00:15:39.674  LOG:  database system is shut down
00:15:40.924  LOG:  database system is ready to accept connections
```

**Probe results (sorted by send time, around the outage)**

| Send time | Path | Status | Notice shown | Project listed |
|---|---|---|---|---|
| 00:15:39.427 | `/` | 200 | no | yes |
| 00:15:39.533 | `/` | **503** | yes | no |
| 00:15:39.638 | `/` | **503** | yes | no |
| 00:15:39.742 | `/` | **503** | yes | no |
| 00:15:39.847 | `/` | 200 | no | yes |
| 00:15:39.953 | `/` | **503** | yes | no |
| 00:15:40.054 | `/api/v1/health` | 200 | — | — |
| 00:15:40.156 – 00:15:40.782 | `/` | **503** ×7 | yes | no |
| 00:15:40.884 | `/` | 200 | no | yes |
| 00:15:41.091 | `/api/v1/health` | 200 | — | — |

Totals for the whole run: `/` returned 200 with the project listed 2,055 times and 503 with the notice 11 times; `/api/v1/health` returned 200 all 230 times. No request errored or timed out.

**App log:** 11 lines of `public database render failed; projects unavailable: (psycopg.OperationalError) connection failed: … server closed the connection unexpectedly`, one per 503.

**After:** `railway deployment list` still showed `79ca6fd3` as the app's deployment, so recovery needed no app restart or redeploy.

**What this shows**
- During the outage, every public request that failed its database read returned 503, showed "Projects temporarily unavailable", and listed no projects.
- The first request after Postgres was ready returned 200 with the project back.
- The health check doesn't use the database, so a 503 on `/` while health stays 200 points at the database, not the app.

**Limits**
- The 200 sent at 00:15:39.847, mid-outage, is unexplained. A likely cause is a request answered by one of the 2 workers over a connection that hadn't closed yet. Not verified.
- The probe didn't check for my name on the 503 pages. The notice is rendered inside the page template, so the page and profile rendered, but profile visibility during a failure is verified by the tests in `tests/test_web.py`, not by this run.
- A first attempt at 00:02:36 (Postgres down about one second) happened after a slower probe had stopped, so it captured no 503. It isn't counted here.

**In my own words:**

&nbsp;
