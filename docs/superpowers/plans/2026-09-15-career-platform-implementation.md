# Career Platform Implementation Plan

> **Execution rule:** Do not begin implementation until this plan is explicitly approved.

## Decisions carried forward from the approved spec

- Audience: recruiters and hiring managers.
- Initial profile: early-career data/analytics/ML professional.
- Product shape: database-backed personal profile site with a minimal admin area.
- Priority: data-driven flexibility while keeping the first release simple and fast.
- Python stack: **FastAPI** backend with explicit database access, authentication, admin APIs, and a separate public frontend.
- Outage strategy: **hybrid fallback** — pre-rendered/static public pages plus a runtime cache containing the most recent successful published profile.
- Public profile availability takes priority over live admin editing during a database outage.

## Task 1: Establish the application foundation

Create the FastAPI application skeleton, environment configuration, and development commands. Use a separate public frontend or server-rendered frontend as appropriate, with FastAPI providing the application/API boundary. Keep runtime configuration separate from source-controlled secrets.

### Done looks like

- The application starts locally with documented commands.
- FastAPI exposes a versioned API boundary for public content and admin operations.
- Development, production, and test configuration have clear boundaries.
- Environment variables are validated at startup.
- No credentials or private values are committed.
- A basic health endpoint or equivalent diagnostic path exists for local verification.

### How to check

- Follow the setup instructions from a clean checkout.
- Start the development server and load the root route.
- Run the repository’s existing lint/type-check command, if available.
- Confirm the health check reports application status without exposing secrets.

## Task 2: Configure the relational database and schema migrations

Set up the relational database connection, migration workflow, and schema definitions for the approved content model: profile, experience, achievements, projects, project highlights, skill categories, skills, education, credentials, and shared content status/order fields. Use SQLAlchemy or SQLModel with Alembic migrations unless the repository already establishes an equivalent Python database convention.

### Done looks like

- A fresh database can be created from migrations alone.
- Relationships and required fields enforce the content model.
- Published/draft/archived states and ordering are represented consistently.
- Seed data can populate a representative profile without hardcoding it into page templates.
- Database access has a single, testable data-access boundary.

### How to check

- Run migrations against a clean local database.
- Run the seed command and inspect the resulting records.
- Run the ORM/database schema validation command, if available.
- Query the seeded records through the application data-access layer.

## Task 3: Implement canonical published-content queries

Create server-side queries/services that return only the published profile content needed by public pages, with deterministic ordering and no accidental draft leakage. Keep the returned shape stable so both page rendering and fallback generation use the same source.

### Done looks like

- Public queries include profile, experience, achievements, projects, highlights, skills, education, and credentials.
- Draft and archived content is excluded from public results.
- Ordering is deterministic and respects explicit sort fields.
- Missing optional content does not break the returned profile.
- Query failures are represented as recoverable errors for the fallback layer.

### How to check

- Seed published, draft, and archived records.
- Verify public queries return only published records in the expected order.
- Verify optional sections can be empty without causing an exception.
- Exercise the database-error path and confirm it returns a fallback-eligible failure rather than a blank response.

## Task 4: Build the public recruiter-facing pages

Implement the public home, about, experience, projects/case studies, skills, education/credentials, contact, and resume-download experiences using the canonical published-content query.

### Done looks like

- A recruiter can understand the person’s target and strengths from the home page quickly.
- Experience and projects show concise summaries, links, dates, tools, and measurable highlights where present.
- Skills are grouped into readable categories.
- Contact details and resume access are easy to find.
- Pages are responsive, keyboard navigable, and use semantic headings/labels.
- Public routes have stable, human-readable URLs and page metadata.

### How to check

- Start the application with seeded content and visit every public route.
- Test at mobile and desktop widths.
- Navigate the complete site with keyboard only.
- Run an existing accessibility or browser test suite, if present.
- Inspect page titles, descriptions, canonical URLs, and social metadata.

## Task 5: Implement the hybrid public-profile fallback

Add the resilience layer selected for this project:

1. Generate pre-rendered/static public profile output from the published canonical content.
2. Cache the most recent successful published profile response at runtime.
3. When the database is unavailable, serve the static output or runtime snapshot instead of an error page.
4. Keep admin editing/live publishing unavailable or read-only until the database recovers.

The fallback must preserve the core profile: headline, summary, experience, projects, skills, education, and contact details.

### Done looks like

- A successful publish/build produces a usable static profile snapshot.
- A successful live request refreshes the runtime cache only with valid published content.
- Simulated database failures still render the public profile.
- The fallback never exposes drafts or archived content.
- The response identifies degraded/read-only mode only if the product UI needs to communicate it; it must not expose implementation details.
- The public response avoids blank pages, unstyled error screens, and broken links.

### How to check

- Load the public site once with the database available so the snapshot/cache is populated.
- Make the database unavailable or inject a controlled data-access failure.
- Reload each public route and verify the profile remains visible.
- Confirm the rendered content matches the last successful published version.
- Verify admin writes fail safely or become read-only while the public pages continue to work.
- Restore the database and confirm new published content replaces the fallback after the next successful generation/request.

## Task 6: Add authenticated minimal admin CRUD

Implement FastAPI authentication and an admin frontend/API for CRUD operations on profile, experience/achievements, projects/highlights, skills/categories, education, credentials, and resume metadata. Include explicit save-draft, publish, archive, and ordering actions.

### Done looks like

- Unauthenticated users cannot access admin routes or mutation endpoints.
- The owner can create and edit each approved content type.
- Drafts are previewable but not public.
- Publishing validates required fields and updates the canonical published content.
- Archive and reorder operations are reflected on public pages after regeneration/cache refresh.
- Admin failure states do not damage the last known-good public profile.

### How to check

- Visit admin routes while signed out and verify access is denied or redirected.
- Sign in and create/edit a draft for each content type.
- Verify drafts do not appear publicly.
- Publish a valid record and verify it appears after the expected refresh.
- Attempt to publish invalid data and verify validation prevents publication.
- Archive and reorder records, then verify public output.

## Task 7: Implement resume generation and media handling

Add secure handling for resume downloads and approved media assets. Generate or render the downloadable resume from the same published canonical data used by the public site, with a stable filename and safe handling of missing optional assets.

### Done looks like

- The resume download is reachable from the public site.
- Published profile data and resume output do not diverge because of duplicated content.
- Uploaded or referenced assets are validated and cannot execute as application code.
- The fallback profile still provides a usable resume link or clearly handles unavailable generation.

### How to check

- Download the resume with representative seeded data.
- Verify name, headline, experience, projects, skills, education, and contact details match published content.
- Test missing images and optional fields.
- Test invalid file types/URLs and verify they are rejected safely.
- Load the resume link while the database is unavailable.

## Task 8: Add SEO, accessibility, performance, and observability checks

Harden the public experience and add focused automated checks around the most important requirements, especially public availability during a database outage.

### Done looks like

- Public pages have consistent metadata and structured content.
- Accessible names, focus states, contrast, and semantic structure meet the project’s chosen baseline.
- Public pages avoid unnecessary database queries and remain fast on the fallback path.
- Application logs distinguish normal rendering, cache/static fallback, and admin/database failures without logging secrets.
- Tests cover published-content filtering, fallback behavior, authentication boundaries, and key public rendering paths.

### How to check

- Run the existing lint, type-check, build, and test commands.
- Run targeted tests for published filtering and database outage fallback.
- Run the project’s available accessibility/performance checks.
- Review logs during normal, fallback, and failed-admin scenarios.
- Confirm no sensitive values appear in logs or generated public output.

## Task 9: Document deployment and recovery procedures

Document local setup, database migration/seed commands, static snapshot generation, runtime-cache behavior, deployment configuration, and the recovery procedure for a database outage.

### Done looks like

- A new developer can run the site and populate sample content.
- Deployment instructions explain how public static output and runtime cache are refreshed.
- The outage runbook explains how to verify fallback availability and restore normal operation.
- Required environment variables and secret handling are documented without including secret values.

### How to check

- Follow the documentation from a clean environment or isolated checkout.
- Perform a migration and seed from the documented commands.
- Run the documented database outage simulation.
- Confirm the documented recovery steps restore live publishing and cache refresh.

## Validation order before release

1. Run schema migrations and seed data.
2. Verify canonical published-content queries.
3. Verify every public route with the database available.
4. Verify the hybrid fallback with the database unavailable.
5. Verify admin authentication and draft/publish/archive behavior.
6. Verify resume download and asset handling.
7. Run targeted tests, then the repository’s full existing validation commands.
8. Perform a production-like build and confirm the static snapshot is deployable.
