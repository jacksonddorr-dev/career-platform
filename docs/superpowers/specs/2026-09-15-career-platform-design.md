# Career Platform Design Spec

## 1. Overview

This project is a database-driven personal resume website for an early-career data/analytics/ML professional targeting recruiters and hiring managers. The system will present a polished public profile while keeping content structured enough to expand into a broader career platform later.

The product begins as a personal professional site, but the architecture must support future growth with minimal redesign: multiple content types, draft/publish workflows, role-specific filtering, portfolio case studies, and a centralized admin experience.

## 2. Product Goal

The first version should help the owner:

- present a clear professional identity to recruiters and hiring managers
- communicate technical depth and measurable impact in a scannable format
- make updates easy without editing application code
- establish a database-backed foundation that can grow into a career platform without a rebuild

## 3. Primary Users

### Recruiters and hiring managers

They want a fast, clear signal of:

- who the person is
- what roles they are targeting
- what tools, skills, and domain experience they have
- where they have applied their work, with proof points and outcomes

### Site owner

They want:

- simple content editing
- low-friction publishing
- flexible content reuse across multiple page layouts
- the ability to add features later without replacing the data model

## 4. Non-Goals

The initial version does not need:

- job search or application tracking
- authentication for site visitors
- multi-user editorial workflows
- payment or subscription features
- AI-generated content or resume parsing
- a social network or community layer

These are out of scope until the platform matures beyond the personal site stage.

## 5. Success Criteria

The initial build is successful if it can:

- publish a polished public landing page and resume-style sections
- support content updates via a structured admin interface instead of hardcoded page content
- make it easy to add projects, experience, skills, and education records
- keep the content model extensible for future platform features
- launch quickly without introducing platform complexity that is not yet needed

## 6. Core Functional Requirements

### 6.1 Public site experience

The site must include these public sections:

- home / hero
- about / summary
- experience timeline
- projects / case studies
- skills and toolkits
- education and credentials
- contact / CTA
- downloadable resume or PDF export

### 6.2 Content management

The owner must be able to manage structured content in a database-backed admin area, including:

- create, update, publish, and archive records
- set ordering of experience and projects
- add summary metrics and outcomes to work entries
- manage skills with categories and proficiency levels
- keep personal profile information centralized

### 6.3 Content states

Every content record should support a minimal lifecycle:

- draft
- published
- archived

This keeps the site stable while allowing content preparation without public exposure.

### 6.4 Searchability and SEO

The site should support:

- static or server-rendered public pages for SEO friendliness
- metadata for title, description, and social preview cards
- structured content for resume and portfolio sections
- clean public URLs for projects and experience entries

### 6.5 Accessibility and responsiveness

The site must be:

- mobile responsive
- readable with keyboard and screen readers
- lightweight enough to load quickly
- visually credible for recruiter evaluation

## 7. Recommended Product Shape

The smallest useful system is a hybrid: a public-facing app backed by a relational database and a minimal admin layer.

### Architecture direction

- frontend: modern server-rendered or static frontend framework
- backend/app: small API + page rendering layer
- database: relational database with normalized tables for reusable content
- storage: file storage for profile photos, project images, PDFs, and attachments
- admin: simple authenticated dashboard for CRUD operations

This design favors simplicity and growth: the system behaves like a CMS for a personal brand, but the data model is specific enough to support platform features later.

## 8. Data Model

The database should reflect content as structured records instead of rendering business logic into templates. The following entities are the minimum useful model.

### 8.1 Profile

Represents the person being represented.

Fields may include:

- id
- full_name
- headline
- location
- email
- website_url
- linkedin_url
- github_url
- summary
- status
- created_at
- updated_at

### 8.2 Experience

Represents work and internships.

Fields may include:

- id
- profile_id
- company_name
- title
- location
- employment_type
- start_date
- end_date
- is_current
- summary
- achievements (as structured bullet text or separate achievement table)
- sort_order
- status

### 8.3 Achievement

Allows measurable impact statements to be stored separately from narrative.

Fields may include:

- id
- experience_id
- text
- metric_value
- metric_label
- sort_order

### 8.4 Project

Represents portfolio work, academic projects, or case studies.

Fields may include:

- id
- profile_id
- title
- short_description
- long_description
- project_url
- repo_url
- status
- start_date
- end_date
- featured
- sort_order

### 8.5 Project highlight

Supports structured evidence and results for projects.

Fields may include:

- id
- project_id
- text
- metric_value
- metric_label
- sort_order

### 8.6 Skill

Represents a skill item that can be grouped by category.

Fields may include:

- id
- profile_id
- name
- category_id
- proficiency_level
- sort_order

### 8.7 Skill category

Supports grouping skills such as Data, ML, Engineering, Business, Tools.

Fields may include:

- id
- profile_id
- name
- sort_order

### 8.8 Education

Represents academic and certification-based profile history.

Fields may include:

- id
- profile_id
- institution_name
- degree_name
- field_of_study
- start_date
- end_date
- gpa
- honors

### 8.9 Certification or credential

Supports continuing education and credentials.

Fields may include:

- id
- profile_id
- title
- issuer
- issue_date
- expiry_date
- credential_url

### 8.10 Resume export data

The public site should be generated from the same data model used by the admin. This protects against scattered content and keeps resume export consistent with what is published publicly.

## 9. Public Pages and Content Flow

### 9.1 Home page

Purpose: quickly establish the professional identity.

Contains:

- name and headline
- short summary
- key skills or domains
- CTA to view work or contact

### 9.2 About page

Purpose: explain career direction and professional narrative.

Contains:

- background summary
- specialization and focus areas
- values or strengths relevant to recruiters

### 9.3 Experience page

Purpose: communicate relevant work history in recruiter-friendly format.

Contains:

- each role with role title, employer, dates, summary, and highlights
- measurable impact statements
- clear emphasis on early-career but credible experience

### 9.4 Project page(s)

Purpose: show applied work and technical depth.

Contains:

- project title and summary
- problem and solution framing
- tools used
- outcomes and metrics
- links to repo/demo/documentation

### 9.5 Skills page

Purpose: make domain expertise easy to scan.

Contains:

- grouped skills by category
- engineering and analytics capabilities
- tool usage and stack familiarity

### 9.6 Contact page

Purpose: convert engaged visitors into contact.

Contains:

- form or contact channels
- clear call to action
- preferred response method

## 10. Admin Experience

The site owner should be able to edit content without writing code. The admin module should be intentionally small but robust.

### Required admin capabilities

- sign in with authenticated admin access
- manage profile information
- add and edit experience entries
- add and edit projects with media and links
- add and edit skills and categories
- add and edit education and credentials
- reorder featured sections
- preview unpublished content
- publish or archive items
- manage resume export generation

### Admin UX principles

- keep forms simple and structured
- save drafts without exposing them publicly
- validate required fields before publishing
- maintain content ordering explicitly

## 11. Platform Growth Path

This design should not block future expansion. The database should enable later phases such as:

- job tracking and opportunities dashboard
- portfolio analytics and page views
- recruiter-facing profile variations or role-specific presentations
- project collections by domain or stack
- content templates for multiple products or personas
- case-study library and portfolio pages for multiple audiences

## 12. Suggested Tech Stack

The recommended implementation for the first version is intentionally lean but scalable.

- frontend: modern React-based framework with server rendering and static generation
- backend: application server for admin and public data rendering
- database: PostgreSQL or equivalent relational database
- ORM: schema-driven data access layer
- auth: simple admin auth with secure session management
- storage: object or file storage for uploaded media and generated resume PDFs

This stack provides clean structure, type-safe data access, and future extension without overbuilding the first release.

## 13. Non-Functional Requirements

### Security

- admin-only editing routes with authentication
- validation and sanitization on all form inputs
- no secret values in source-controlled config
- safe handling of uploaded files and URLs

### Performance

- public pages should render quickly
- data fetching should be efficient and avoid over-querying
- static site generation should be used where practical

### Maintainability

- content and code should be separated by clear responsibilities
- schema changes should be explicit and versioned
- public pages should consume the same canonical content model as the admin

## 14. Risks and Mitigations

### Risk: overbuilding the platform too early
Mitigation: keep the first release focused on the personal brand site and delay platform features until needed.

### Risk: content duplication across pages
Mitigation: centralize data into canonical records and generate page content from the same model.

### Risk: brittle admin workflows
Mitigation: use structured forms, validation, and a clear publish lifecycle.

### Risk: resume content not matching actual professional narrative
Mitigation: define a single source of truth for profile and work details and use it consistently across public pages and export.

## 15. Scope for v1

The v1 release should include:

- public personal brand pages
- structured content management using a database
- admin dashboard for key sections
- publish/archive workflow
- PDF or downloadable resume export
- responsive recruiter-focused design

Everything beyond v1 can be treated as future platform work.

## 16. Recommendation

The best fit for this project is a lightweight, database-backed personal brand and portfolio site with a minimal admin layer. It preserves speed and simplicity while creating a durable foundation for later platform growth.

This approach satisfies the immediate recruiter-facing objective without locking the project into a static, hardcoded structure that would require a rewrite later.
