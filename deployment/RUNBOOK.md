# Production runbook

For a separate synthetic-data environment, use [STAGING.md](STAGING.md) and the standalone staging Compose file. Do not overlay it on production.

## Repository setup

Run commands from the repository root. Use Python 3.12 or newer and PostgreSQL.
Install `requirements-dev.txt` for local checks and tests; production images install
both `requirements.txt` and `deployment/requirements-production.txt`.
Docker with Compose is required for the container commands below.
Copy `deployment/.env.production.example` to `.env.production` in the repository
root and supply the real service credentials. Run Compose from the root with
`docker compose -f deployment/docker-compose.production.yml build`.
Keep the paired `DB_NAME`/`POSTGRES_DB`, `DB_USER`/`POSTGRES_USER`, and
`DB_PASSWORD`/`POSTGRES_PASSWORD` values consistent for a new database volume.
Changing these values does not change credentials in an existing PostgreSQL volume.
Add `FRONTEND_URL` with the deployed frontend URL so verification and reset links
do not point to localhost.

Compose loads `.env.production` through `env_file`; ordinary `manage.py` commands
do not load that file automatically. Commands outside Compose need production
variables supplied by the environment, including
`DJANGO_SETTINGS_MODULE=Business_management_backend.settings_production`.
The backend listens on port 8000 inside the Compose network; configure an HTTPS
reverse proxy before exposing it. Static files are collected during the image
build without production credentials and served through WhiteNoise.

## Existing database upgrade

The new security migration preserves records while converting legacy numeric IDs
to UUIDs, including login-history session references. Existing numeric IDs become
UUIDs with the same integer value. Existing OTP challenges and browser-fingerprint
trust records are invalidated: users must verify by email and trust their device
again. This migration is PostgreSQL-specific and cannot be automatically reversed.
Stop application writers and back up the database before applying it. The upgrade
has a populated legacy-schema regression test in the test database; it has not
been applied to the application's configured database as part of the repair.
Check the target database's migration state instead of assuming it has been upgraded.

Review the migration plan in the target environment, then apply migrations during deployment.
The new employee and invitation uniqueness constraints reject existing duplicate
records rather than silently deleting them; resolve any duplicates before retrying.

## Login integration

An untrusted login returns HTTP 202 with flat `otp_required: true`, `challenge_id`,
`email`, `message`, and `expires_in` fields. Send `challenge_id` and the string
`code` to `/api/v1/auth/verify-otp/`; email is optional. With JSON
`trust_device: true`, successful verification returns a `trusted_device_token`.
Store it securely and send it in the `X-SmartBiz-Device-Token` header on subsequent
password logins. The old `/api/v1/verify-otp/` route and `device_token` response/body
field remain supported. Use the newest emailed code and its matching challenge;
requesting another code invalidates the previous challenge. Only the device token's
hash is stored in the database. Refresh rotation updates the corresponding active
session; clients must retain the newly returned refresh token.

## Before deploy

- Back up PostgreSQL and verify restore credentials.
- Confirm object-storage bucket is private and signed URLs expire quickly.
- Confirm Redis is not publicly reachable.
- Confirm secrets are supplied by the deployment secret store, never committed env files.
- Run backend checks, the migration plan, tests, and OpenAPI generation/validation.
- Run frontend checks separately in the frontend repository, if deploying one.
- Review pending migrations for locks/table rewrites and schedule maintenance where necessary.

## Deploy order

For an existing deployment, stop all writers and take a verified backup before the
security upgrade. It is not a rolling, backward-compatible migration.

1. Build the image with the command above.
2. Start infrastructure with `docker compose -f deployment/docker-compose.production.yml up -d db redis`; wait until PostgreSQL is healthy and Redis is ready.
3. Review the plan with `docker compose -f deployment/docker-compose.production.yml run --rm --no-deps backend python manage.py migrate --plan`.
4. Apply the reviewed migrations with `docker compose -f deployment/docker-compose.production.yml run --rm --no-deps backend python manage.py migrate --noinput`.
5. Start the application with `docker compose -f deployment/docker-compose.production.yml up -d backend worker` and verify startup logs and connectivity.
6. Start the scheduler with `docker compose -f deployment/docker-compose.production.yml up -d scheduler` after the web process and worker are healthy. Keep only one scheduler instance.
7. Configure HTTPS routing and deploy the frontend, if applicable.
8. Smoke test login, OTP, refresh, `/api/v1/users/me/`, company setup, one tenant workflow, private file download, support tickets, and `/api/platform/v1/dashboard/` using the appropriate accounts.

The Compose file does not define an HTTPS proxy, published backend port, or
application health checks. Infrastructure startup order alone is not a readiness check.

## Verification limits

### Reporting worker schedule

Production Beat queues `reporting_schedules.tasks.process_reporting` every minute.
The task generates obligations for each company's local date, marks overdue drafts
and pending obligations missed, then creates in-app reminders. Morning reminders
start at 08:00 company-local time; final reminders occur within one hour of the
deadline. The reminders do not send email. Generation uses unique obligations;
reminder flags and notifications commit together under row locks to tolerate retries.
Failed tasks are visible in worker logs; the next periodic run retries outstanding work.
This does not backfill dates missed during a multi-day outage.

Run a single Beat instance and monitor worker failures and queue age. Verify all
three management commands against staging data before enabling the scheduler.
Production startup now requires FRONTEND_URL; set it to the public frontend origin.

The backend passed 147 tests on 2026-09-19, including strict API schema generation
and real-response checks for login, OTP, dashboard and onboarding. Generate the
schema with `python manage.py spectacular --file openapi-v1.yaml --validate --fail-on-warn`;
`scripts/verify_backend.py` uses the same strict check. The schema no longer emits
generation warnings or errors. Other response paths still benefit from additional
runtime contract coverage. Docker was unavailable during local verification, so a
full image build and container smoke test still need to run in a Docker environment.

## Rollback

- Roll back application containers only when the previous code supports the current database schema.
- For the irreversible security upgrade, restore a compatible database backup and application version together during a maintenance window if rollback is necessary.
- Do not reverse destructive migrations automatically.
- Restore database only after confirming data-loss scope and stopping writers.
- Revoke compromised sessions/keys if the rollback is security-related.

## Backups

- Automated encrypted PostgreSQL backups with point-in-time recovery where supported.
- Versioned/private object storage with lifecycle retention appropriate to each classification.
- Perform recurring restore drills; an untested backup is not considered sufficient.

## Monitoring

Alert on elevated 5xx rates, login failures/lockouts, worker queue age, failed scheduled jobs, DB saturation, Redis failures, storage errors, malware scan failures, email queue failures, and security/audit pipeline failures.

## Personal appearance

Each user has a `theme_preference` of `system` (default), `light`, or `dark`.
`GET /api/v1/users/me/` returns it. Authenticated users save their own choice with
`PATCH /api/v1/users/me/preferences/` and JSON `{"theme_preference":"dark"}`.
The endpoint always updates the authenticated user; company settings are unaffected.
The frontend applies the selection immediately and follows device appearance changes
when System is selected. Failed saves display an error and restore the saved choice.


### Platform service monitoring

Apply platform_admin migration 0002 before starting updated workers. Reporting
results are stored in PostgreSQL, so the web and worker share evidence even when
using separate caches. Production Beat also queues `platform_admin.tasks.monitor_services`
every five minutes. Keep the worker and one scheduler running using the deployment
steps above. A result older than 15 minutes needs attention; reporting evidence
expires after three minutes. Local `runserver` alone does not start scheduled jobs.

For an explicit connectivity check, run `python manage.py check_platform_services`
in the application's environment. It connects and authenticates to SMTP without
sending email, and writes, reads, and deletes a unique file under `.healthchecks/`
in configured storage. Give the worker access to that prefix. SMTP connectivity
does not prove inbox delivery; storage availability does not prove privacy.
The health API only reads these saved probe results; it never sends email or writes
storage objects on page refresh. Provider error details and credentials are not
included in the health response.

Backups are still unmonitored. Before launch, select a protected backup destination,
configure automated PostgreSQL and uploaded-file backups with retention, and
perform an isolated restore drill. Do not restore over the live database or label
backup protection healthy based solely on a configured schedule or a file's existence.
This service-monitoring change does not create or schedule backups.


### Local Windows automation without Redis

With development settings and PostgreSQL, run
`./Business/Scripts/python.exe manage.py run_local_automation` in a separate
terminal alongside the web server. It runs the actual reporting workflow every
minute (including due in-app reminders) and SMTP/storage probes every five minutes.
`--once` performs a single cycle for diagnostics. A PostgreSQL advisory lock prevents
a second local runner from running concurrently. The runner refuses production
settings; do not run it alongside Celery reporting workers against the same database.
Stop it with Ctrl+C. This foreground process does not survive Windows restart;
restart it with the same command during local development. Production uses the
Compose worker and scheduler with restart policies described above instead.

Service health becomes stale if the runner stops. A running web server alone is
not evidence that automation is operating. Backups require a separate protected
destination and remain unmonitored until a backup and restore process is connected.


### Encrypted backup tooling

See `docs/backup-and-recovery.md` for the configured-destination backup command,
optional daily production scheduling, and isolated recovery preparation. These
commands require the destination and key; they have not copied live data as part
of implementation. Recovery verification and retention configuration remain
operator tasks.


### Form attachments and safe publication

Install the updated requirements (including pypdf), then apply migrations through
forms_engine 0021. Migration 0020 adds the actor/company-bound draft retry key;
0021 only adds minimum zero to unchanged monetary library definitions. Company
copies, existing entries and customized library questions are preserved.

Production settings require a clean malware verdict before uploads are stored.
Configure ATTACHMENT_SCANNER=documents.scanning.clamav, CLAMAV_HOST and
CLAMAV_PORT to an operator-provisioned ClamAV daemon on a private network.
Keep signatures updated, enable INSTREAM and set its stream limit to at least
25 MB. Never expose the ClamAV socket publicly. The daemon is not provisioned by
this change. An unavailable scanner blocks uploads with a recoverable message;
it does not discard the saved draft. Development permits content checks without
a scanner. Do not disable the production requirement to work around an outage.

Before release, verify clean and infected test files against the actual scanner,
private storage/download access and proxy request limits in staging. Content
checks reject renamed binary files, invalid/encrypted PDFs, unsafe Office ZIP
containers and malformed images; they do not replace malware scanning.


### Private scanner deployment and verification

The optional `deployment/docker-compose.scanner.yml` adds the official ClamAV
container, a persistent signature volume and a private application/scanner network.
It exposes no host port and mounts no company uploads. Its separate update network
allows signature downloads. The backend waits for the image's built-in healthcheck.
Reserve 4 GiB for the scanner in addition to the application's requirements.
Review `CLAMAV_IMAGE` and pin a supported image/digest before release; the example
uses the documented 1.4 feature-release image. Follow the official image's update
and end-of-life guidance: https://docs.clamav.net/manual/Installing/Docker.html.

From the repository root on the deployment host, use the same explicit environment
and Compose files for every command:

```sh
docker compose --env-file .env.production -f deployment/docker-compose.production.yml -f deployment/docker-compose.scanner.yml config --quiet
docker compose --env-file .env.production -f deployment/docker-compose.production.yml -f deployment/docker-compose.scanner.yml up -d clamav
docker compose --env-file .env.production -f deployment/docker-compose.production.yml -f deployment/docker-compose.scanner.yml ps clamav
```

Wait for healthy status and check signature update logs. Configure the daemon's
StreamMaxLength, MaxFileSize and MaxScanSize for the application limit and archive
policy; a clean 25 MiB probe below must pass. The image's healthcheck proves daemon
readiness only, not successful detection. After the backend is running with the
same configuration, execute:

```sh
docker compose --env-file .env.production -f deployment/docker-compose.production.yml -f deployment/docker-compose.scanner.yml exec backend python manage.py check_attachment_scanner --test-detection --test-upload-limit
```

This sends synthetic clean content, a 25 MiB clean stream and the harmless standard
EICAR antivirus test string directly to the configured scanner in memory. It does
not create submissions, persist files or change company data. An explicit clean
verdict and an explicit rejected test verdict are required. Scanner errors and
missing configuration fail the command. Running without `--test-detection` cannot
certify detection. Run this in isolated staging first; antivirus monitoring may
record the synthetic test detection.

Then verify a clean file through the actual staging form and a scanner outage:
the clean upload succeeds; an unavailable scanner blocks the upload and keeps its
draft available for retry. Restore the scanner and retry on that same draft. Check
that rejected uploads produced no storage objects. Do not stop the live production
scanner to perform the outage test. Existing production processes are not started,
reconfigured or deployed by adding these files.
