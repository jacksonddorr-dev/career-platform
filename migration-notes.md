# Migration notes: Railway → AWS (EC2 + RDS)

Running log for `docs/superpowers/plans/2026-11-03-aws-ec2-rds-migration.md`. Each deviation from the plan gets an entry: what the plan said, what happened, why, and what it affects. This repo is public, so no passwords, IP addresses, or connection strings go here.

## Current state (2026-11-09)

| Thing | State |
|---|---|
| Live site | **Down.** `https://jacksoncareer.me` returns Railway's 404 "Application not found". DNS still points at Railway. |
| Railway | Trial ended 2026-11-06. The `career-platform` service shows *Failed*, and all Postgres deployments are *REMOVED*. The database can't be reached. |
| Latest data | `railway-20261029T220722Z.dump` on the laptop only (restore-tested 2026-10-29, checksum on file). Nothing newer exists. |
| AWS | Security groups, subnet group, RDS instance (accepted 2026-11-03), and EC2 instance (running 2026-11-03) exist. No Elastic IP. The RDS settings check hasn't been read back. |
| Code | Branch `aws-ec2-rds-migration`, nothing committed or pushed. Task 1 not started. |

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
