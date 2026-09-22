# Business Management Backend

Django REST API with PostgreSQL for company administration, projects, reporting,
workflows, documents, and support.

## Local setup

Run commands from the repository root. Use Python 3.12 or newer (the Docker image
uses Python 3.13). Create and activate a virtual environment, then install the
development dependencies with `python -m pip install -r requirements-dev.txt`.
Docker is optional for local development.

Start PostgreSQL and create a database and database user. Configure `.env` in the
repository root with `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
and `DB_PORT`. Use a strong secret key and keep `.env` private. For local HTTP
development, set `DEBUG=True`; otherwise HTTPS redirects are enabled.

With `DEBUG=True`, email defaults to the console backend: verification messages
appear in the server terminal instead of being delivered. Configure SMTP when
actual delivery is needed. Tests capture mail locally without sending it.
If connecting a frontend, set `FRONTEND_URL` and `CORS_ALLOWED_ORIGINS` to its origin.

Before upgrading an existing database, read the migration notes in
[the deployment runbook](deployment/RUNBOOK.md). For a new database, run
`python manage.py migrate`, then `python manage.py runserver`.
API routes use `/api/v1/`; internal administration is at `/internal/admin/`.
Create a platform administrator with `python manage.py createsuperuser` if needed.
API documentation is exposed at `/api/v1/docs/` only when `DEBUG=True`.

## Verification

```text
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -q
```

Tests require PostgreSQL and permission to create a separate test database and a
temporary schema within it. They do not apply migrations to the application database. Run
test processes sequentially unless each has a distinct test database name.

Production setup, the database upgrade procedure, and the OTP login contract are
documented in [deployment/RUNBOOK.md](deployment/RUNBOOK.md).

API schema generation is checked with `--validate --fail-on-warn`, including in
the regression suite. Passing local checks alone does not establish deployment readiness.

## Architecture and maintenance rules

The backend is the security authority. Tenant APIs use `/api/v1/`; platform
administration uses `/api/platform/v1/`. The frontend is maintained in the sibling
[business_management_frontend](../business_management_frontend/README.md) repository.
Django Admin remains an operational alternative, not a prerequisite for daily work.

- Authenticate and establish tenant/platform context before querying business data.
  Enforce capabilities, object visibility, sensitive-field disclosure, business state,
  and subscription entitlement server-side. Platform authority is not tenant access.
- Use explicit serializer fields and backend `allowed_actions`. New model fields must
  not silently expand API disclosure. Use domain services for lifecycle transitions,
  locking, numbering, audit and notifications after transaction commit.
- Form configuration, submission, reading answers, approval and fulfillment are
  separate authorities. Preserve published versions and historical schema snapshots.
- Plan items, attachments, records and derived systems inherit source visibility.
  Search, exports, notifications, analytics and chat must not broaden disclosure.
- Keep audit/history immutable where required; do not rewrite historical authorship
  during employee replacement. Test last-admin and account/session revocation rules.
- Keep files private and authorize downloads. Location is explicit event evidence,
  not continuous tracking. Protect anonymous sources and classified fields across
  all representations, including exports and support.

These are maintenance requirements, not a claim that every production path has been
certified. The implementation and regression tests determine current behavior.
Do not overwrite this repository with cumulative ZIPs: compare and selectively
integrate changes, then rerun relevant tests.

## Release verification

Both codebases are available and run locally. Selected authenticated screens and
focused regression suites have been verified; a public production launch is not yet
certified. Local checks do not replace staging evidence.

Before release, verify fresh PostgreSQL setup and an existing-database upgrade,
full functional/security tests, concurrency and delegation, and complete journeys
with two companies and employee/manager/company-admin/platform identities. Include
forms/versioning, requests and approvals, employee replacement, subscription capacity,
private downloads, anonymous/sensitive data and secondary-system visibility.

Run `python scripts/verify_frontend_contracts.py` from this repository to check the
paired frontend routes/capability names. This checks static contracts, not runtime
payloads or authorization. Use `python scripts/verify_system.py --help` for the
integrated verification options. Generate/review migrations only when required;
do not blindly generate them during deployment.

Use private staging to verify HTTPS, API origins, auth/OTP/refresh/logout/reset,
rate limits, email/retries, scheduled jobs/timezones, storage scanning and retention,
subscription entitlements, performance with representative data, monitoring and
alerts. Rehearse backup restoration and rollback before a controlled pilot.

## Documentation

- [Deployment and recovery runbook](deployment/RUNBOOK.md): production configuration,
  migration cautions, authentication integration and operational procedures.
- [Frontend control inventory](deployment/FRONTEND_CONTROL_INVENTORY.md) and
  [API route audit](deployment/FRONTEND_API_ROUTE_AUDIT.md): integration references.
- [Platform administration parity](deployment/PLATFORM_ADMINISTRATION_PARITY.md):
  frontend administration coverage and boundaries.
- [Selective integration decisions](deployment/ZIP_IDEAS_FOLLOWUP.md) and
  [original ZIP review](deployment/ZIP_INTEGRATION.md): historical decision records,
  not installation instructions or current readiness certificates.

This README replaces the numbered phase READMEs. Their useful security principles
and release checks are consolidated above; obsolete overlay-installation instructions
and historical scan counts are intentionally omitted.
