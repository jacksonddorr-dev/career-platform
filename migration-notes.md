# Migration notes: Railway → AWS (EC2 + RDS)

Running log for `docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md`. Each deviation from the plan gets an entry: what the plan said, what happened, why, and what it affects. This repo is public, so no passwords, IP addresses, or connection strings go here.

## Current state (2026-11-09, end of Stage B)

| Thing | State |
|---|---|
| Live site | **Still down.** DNS still points at Railway, which returns 404. |
| AWS app | Running on EC2 at `9fcc825` under systemd, behind no public port yet: HTTPS on 443 and HTTP→HTTPS on 80 are open with a valid Let's Encrypt certificate; SSH on 22 from one laptop IP. Passed the reboot, database-outage, and bad-migration tests. |
| AWS database | RDS 18.6, Single-AZ, private, encrypted, 1-day backups, deletion protection. Holds the 2026-10-29 data; fingerprint matches the reference. |
| Data | `railway-20261029T220722Z.dump` plus `.sha256` and `.fp` in `~/backups/career-platform/`. **The second copy outside the laptop (Task 2 Step 4) is still open.** |
| Code | Branch `aws-ec2-rds-migration` pushed (`fc760ba`, `9fcc825`). Not merged to `main`. |
| Next | Jackson's admin-login check, then Task 6 (DNS switch) with Jackson's approval. Task 7 Step 1 due before 2026-11-17. |

## Deviations

### D1 — RDS backup retention 7 days → 1 day (2026-11-03)
- **Plan:** `--backup-retention-period 7` (Decisions table, Task 3 Step 4).
- **What happened:** `CreateDBInstance` failed with `FreeTierRestrictionError`: "The specified backup retention period exceeds the maximum available to free tier customers." The account is on AWS's free plan, which the plan didn't know. Jackson chose 1 day, and AWS accepted it.
- **Affects:** point-in-time restore reaches back only about a day. Dumps outside AWS are the real long-term backup. The Task 7 restore test still works within that window. Plan updated.

### D2 — Tasks run out of order (2026-11-03)
- **Plan:** Stage A (Task 1 code, Task 2 fresh backup) before Stage B (Tasks 3–4).
- **What happened:** Jackson asked for the RDS database and then the EC2 instance first, so Tasks 3 and 4 Steps 1–2 ran before Tasks 1 and 2.
- **Affects:** nothing technical, because the AWS resources don't depend on the code changes. Charges started earlier, at about $0.93/day.

### D3 — Hard-deadline backup (Task 2) missed; Railway data gone (found 2026-11-09)
- **Plan:** Task 2, "hard deadline 2026-11-05": a fresh dump, test-restored and copied outside AWS, before the trial ended.
- **What happened:** It wasn't run. The trial ended 2026-11-06, and the Railway database is no longer reachable.
- **Affects:**
  - **Data:** the migration has to use the 2026-10-29 dump. Any admin edits made after 2026-10-29 22:07 UTC are lost unless Railway still holds the volume and it can be recovered. *Open question for Jackson.*
  - **Downtime:** the site has been down since the trial ended. Jackson accepted downtime on 2026-11-03 rather than paying Railway.
  - **Rollback:** Task 6's rollback (point DNS back at Railway) no longer exists. The fallback is now: keep DNS where it is until AWS passes every check.
  - **Plan steps that change:** Task 2 Steps 1–2 and Task 6 Step 2 (fresh dumps from Railway) can't run. Task 6 Step 3 restores the 2026-10-29 dump instead. Task 2 Steps 3–4 (local restore test, second copy) still apply to that dump.

### D4 — Second copy of the backup not yet made (2026-11-09)
- **Plan:** Task 2 Step 4, a copy outside AWS and off the laptop.
- **What happened:** The only copy is on the laptop.
- **Affects:** losing the laptop now means losing the site's data. Do this first.

### D5 — The 2026-10-29 reference fingerprint has to be rebuilt (2026-11-09)
- **Plan:** Task 2 Step 2 fingerprints production on Railway, and later steps compare against that.
- **What happened:** Railway is gone, and the 2026-10-29 fingerprint files were in a temporary folder that no longer exists.
- **Affects:** the reference fingerprint now comes from restoring the 2026-10-29 dump locally. That's equivalent: on 2026-10-29 the local restore of this dump matched production exactly (all 11 tables and 10 sequences).

### D6 — Laptop IP changed; SSH rule replaced (2026-11-09)
- **Plan:** port 22 allowed from the laptop's IP, set once in Task 3 Step 2.
- **What happened:** the laptop's public IP changed between 2026-11-03 and 2026-11-09, so SSH would have been refused. The old `/32` rule was replaced with the current one before continuing.
- **Affects:** this will happen again whenever the IP changes. Fix: `authorize-security-group-ingress` for the new IP, then `revoke-security-group-ingress` for the old one, on `career-web-sg`.

### D7 — Database-outage test used the server's firewall, not the security group (2026-11-09)
- **Plan:** Task 4 Step 11(b), remove the 5432 rule from `career-db-sg`.
- **What happened:** security groups track open connections, so removing the rule wouldn't cut the app's existing pooled connections, and the test could falsely pass. Instead, `iptables` on the EC2 instance rejected outbound 5432, with a 3-minute automatic undo as a safety net, then was removed by hand after about a second.
- **Affects:** nothing in AWS changed. The test is stricter than the plan's version, because it cuts existing connections too.

### D8 — `deploy.sh` hid the reason for a failed deploy; fixed (2026-11-09)
- **Plan:** Task 1 Step 9, `deploy.sh` prints the last 30 log lines and exits 1 on failure.
- **What happened:** with a failing migration, `systemctl restart` itself fails, and `set -e` exited before the logs were printed. The bad-migration test (Task 4 Step 11c) found this. Fixed with a test in `9fcc825`, then verified by re-running the test.
- **Also learned:** on a single server, a failed deploy takes the site down until you roll back with `./deploy/deploy.sh <previous ref>`. There's no old version still serving.

### D9 — No separate final data load at cutover (2026-11-09)
- **Plan:** Task 6 Steps 2–3, take a fresh Railway dump at cutover, then drop and re-restore RDS.
- **What happened:** Railway is gone (D3), and Jackson confirmed no edits after 2026-10-29. So Task 4 Step 6's restore of the 2026-10-29 dump is already the final data.
- **Affects:** Task 6 Steps 2–3 become "check the RDS fingerprint still matches the reference" instead of re-restoring. Admin edits must still wait until after the switch.

### D10 — certbot account registered without an email (2026-11-09)
- **Plan:** Task 5 Step 1 didn't say.
- **What happened:** certbot ran with `--register-unsafely-without-email`, so Let's Encrypt has no contact address for this certificate.
- **Affects:** no expiry warnings by email. Expiry is covered instead by certbot's renewal timer and the uptime check in Task 7 Step 3. Add an email later with `certbot update_account --email ...` if wanted.

### D11 — The Cloudflare token expires, which sets a deadline (2026-11-09)
- **Plan:** Task 5 Step 1, a token restricted to DNS Edit on this zone. Task 7 Step 1 removes it "after DNS has settled", with no date.
- **What happened:** Jackson also restricted the token to the server's Elastic IP and set it to expire 2026-11-17 07:59 UTC (end of 2026-11-16 Pacific). That's safer, but renewal is still set to use the token.
- **Affects:** Task 7 Step 1 (switch renewal to HTTP, delete the token) must happen **before 2026-11-17**. The certificate itself lasts until 2027-02-07.
