# Project 1 submission: Own Your Corner of the Internet

| | |
|---|---|
| Student | Jackson Dorr |
| Repository | https://github.com/jacksonddorr-dev/career-platform |
| Live site | https://jacksoncareer.me (`http://` and `www.` redirect there) |
| Final commit | The SHA submitted in Brightspace. It's the latest commit on `main`. |
| Index written | 2026-10-26 |

This index only links to evidence. Explanations live in the [README](../README.md) and the linked files. Notes marked "written afterward" were added while reconstructing the record on 2026-10-25/26 and are labeled where they appear.

## 1. README, original spec, and plans

- [README](../README.md)
- [Original design spec](superpowers/specs/2026-09-15-career-platform-design.md). Its section 12.1, written afterward, explains the SQLite choice.
- [Implementation plan](superpowers/plans/2026-09-15-career-platform-implementation.md)
- [Azure VM migration plan](superpowers/plans/2026-09-24-azure-vm-migration.md)
- [Operate-the-VM plan](superpowers/plans/2026-10-01-operate-the-vm.md)
- [Railway and PostgreSQL migration plan](superpowers/plans/2026-10-10-railway-postgres-migration.md), which also serves as the Railway spec ([why](../TASKS.md#4-railway-and-postgresql-migration))

## 2. Architecture diagrams (including email and analytics)

- [`docs/request-path.md`](request-path.md): Azure, Railway with the `www` redirect, email, and analytics
- [README: Architecture](../README.md#architecture)

## 3. Migration: plan, data comparison, cutover, rollback

- Plan committed before the deployment changed: [`f5fa2d1`](https://github.com/jacksonddorr-dev/career-platform/commit/f5fa2d1) … [`7cd922f`](https://github.com/jacksonddorr-dev/career-platform/commit/7cd922f) (2026-10-11 00:14–00:21 UTC)
- [Dependency inventory (*Starting state*)](superpowers/plans/2026-10-10-railway-postgres-migration.md#starting-state-inspected-2026-10-10)
- Compatibility fixes: [`f5fa2d1`](https://github.com/jacksonddorr-dev/career-platform/commit/f5fa2d1) driver URL and `%` in password, [`0ca8844`](https://github.com/jacksonddorr-dev/career-platform/commit/0ca8844) enum on downgrade, [`e4907ee`](https://github.com/jacksonddorr-dev/career-platform/commit/e4907ee) copy with ids and sequence reset; tests: [`tests/test_postgres.py`](../tests/test_postgres.py), [`tests/test_copy_db.py`](../tests/test_copy_db.py)
- [Backup, copy, row-by-row comparison, sequence check, and why it isn't re-seeded data (Task 5)](superpowers/plans/2026-10-10-railway-postgres-migration.md#task-5-configure-railway-deploy-copy-the-data-jackson-in-dashboard--laptop)
- [Rendered-page comparison: not done (Task 5 Step 6)](superpowers/plans/2026-10-10-railway-postgres-migration.md#task-5-configure-railway-deploy-copy-the-data-jackson-in-dashboard--laptop)
- [Cutover record: times, DNS before and after, later checks](superpowers/plans/2026-10-10-railway-postgres-migration.md#record-written-2026-10-26-after-the-cutover) (written afterward)
- [README: How the migration preserved the data](../README.md#how-the-migration-preserved-the-data)
- [README: Azure to Railway, who manages what](../README.md#azure-to-railway-who-manages-what)
- [README: Rolling back a bad change](../README.md#rolling-back-a-bad-change) (data steps untested)

## 4. Azure HTTP and restart evidence; final DNS and HTTPS

- [`docs/evidence/ex03.md`](evidence/ex03.md) and [screenshot](evidence/ex03-site.png): Azure build and first run
- [Azure plan: Verify](superpowers/plans/2026-09-24-azure-vm-migration.md#8-verify) and [replacing the demo content](superpowers/plans/2026-09-24-azure-vm-migration.md#9-content-replace-the-seeded-demo-profile-with-jacksons-resume-added-2026-09-30)
- Operate-the-VM plan: [nginx](superpowers/plans/2026-10-01-operate-the-vm.md#1-nginx-the-front-door-on-port-80), [systemd](superpowers/plans/2026-10-01-operate-the-vm.md#2-systemd-keep-the-app-running), [10 verification checks](superpowers/plans/2026-10-01-operate-the-vm.md#3-verify), [ports, addresses, NSG rules](superpowers/plans/2026-10-01-operate-the-vm.md#4-record)
- [Restart evidence and the VM's deletion on 2026-10-13](superpowers/plans/2026-10-01-operate-the-vm.md#5-decommissioned-added-2026-10-26)
- [Azure HTTPS: Exercise 4 write-up](how-this-site-is-secured.md) and [addendum](how-this-site-is-secured.md#addendum-azure-https-setup-record-written-2026-10-26-after-the-vm-was-deleted)
- [Final DNS records and their purposes](evidence/dns-final.md); [before Zoho](evidence/dns-before-zoho.md)
- [Final HTTPS: Railway certificate and renewal](how-this-site-is-secured.md#addendum-railway-certificate-recorded-2026-10-26)
- [`www` redirect, `http://www` and `https://www` verified](evidence/www-redirect.md)
- [DNS/TLS investigation, a deliberate simulated lab](evidence/ex05.md)

## 5. Reviewed change through Railway

- [`docs/evidence/reviewed-change.md`](evidence/reviewed-change.md): [`4afc2ee`](https://github.com/jacksonddorr-dev/career-platform/commit/4afc2ee) → Railway deployment `79ca6fd3` → live 503 behavior
- [Live database failure → 503 → recovery → 200](../TASKS.md#record-live-database-failure--503--recovery--200-2026-10-26-utc)
- [Railway service-variable fix (Task 5 Step 1)](superpowers/plans/2026-10-10-railway-postgres-migration.md#task-5-configure-railway-deploy-copy-the-data-jackson-in-dashboard--laptop)

## 6. Zoho email

- [Sending, receiving, replying, before-MX line](evidence/ex06.md#1-email-tests)
- [MX, SPF, DKIM, DMARC records](evidence/ex06.md#2-spf-dkim-and-dmarc-results), [Cloudflare screenshot](evidence/ex06-TXTs.png), [final DNS](evidence/dns-final.md)
- [Header analysis: SPF, DKIM, DMARC pass](evidence/zoho-header-check.md)
- [README: Decisions, managed vs. self-hosted email](../README.md#decisions)

## 7. GA4

- [Realtime check: page view and outbound click](evidence/ex06.md#realtime-check-2026-10-25-pdt); [Events list screenshot](evidence/ex06-q3.png)
- [README: Analytics (GA4)](../README.md#analytics-ga4)

## 8. Failures, decisions, reflection, costs, limitations

- [README: Investigated failures](../README.md#investigated-failures): [`ex03.md`](evidence/ex03.md) (application dependency), [`www-redirect.md`](evidence/www-redirect.md) (DNS, real), [`ex05.md`](evidence/ex05.md) (DNS/TLS, deliberate lab), [`postgres-password-rotation.md`](evidence/postgres-password-rotation.md) (Railway build failure)
- [README: Decisions](../README.md#decisions) (reconstructed 2026-10-26; the in-class originals were lost)
- [README: Reflection](../README.md#reflection)
- [README: Costs, credits, and cleanup](../README.md#costs-credits-and-cleanup) (Railway trial ends 2026-11-06)
- [README: Remaining limitations](../README.md#remaining-limitations)

## Not done or unverified

- [No pre-MX email test](evidence/ex06.md#1-email-tests)
- [No rendered-page or PDF comparison before cutover](superpowers/plans/2026-10-10-railway-postgres-migration.md#task-5-configure-railway-deploy-copy-the-data-jackson-in-dashboard--laptop)
- [No checks recorded on the cutover day; the deployed commit `7cd922f` is inferred](superpowers/plans/2026-10-10-railway-postgres-migration.md#record-written-2026-10-26-after-the-cutover)
- [No deliberate VM restart test](superpowers/plans/2026-10-01-operate-the-vm.md#5-decommissioned-added-2026-10-26); [certbot and nginx HTTPS configuration not saved](how-this-site-is-secured.md#addendum-azure-https-setup-record-written-2026-10-26-after-the-vm-was-deleted)
- [Data rollback untested, no production database backup](../README.md#rolling-back-a-bad-change)
- [Use of the default session secret before 2026-10-26 unknown](superpowers/plans/2026-10-10-railway-postgres-migration.md#task-5-configure-railway-deploy-copy-the-data-jackson-in-dashboard--laptop)
