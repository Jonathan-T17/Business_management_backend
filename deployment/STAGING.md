# Isolated staging preparation

Prepared 15 October 2026. No hosting account is required to prepare these files. Actual deployment requires a Docker/Compose host, HTTPS routing, a separate private file bucket and a test email service. This stack has not been started locally because Docker is unavailable here.

## Files and boundaries

For a researched compute/storage/test-email comparison, see [HOSTING_OPTIONS.md](HOSTING_OPTIONS.md). Budget and region must be settled before provisioning.

- `docker-compose.staging.yml` is standalone. Do not combine it with the production Compose file.
- Copy `deployment/.env.staging.example` to `.env.staging` at the repository root. The real file is ignored by Git and the Docker context. No real credentials were generated or copied during preparation.
- Use new staging-only credentials, a database and bucket containing `staging` in their names, synthetic company data and test recipients. Naming is a guardrail, not proof of resource isolation: verify the actual provider account/bucket/database too.
- Copy the public values in `frontend.staging.env.example` into the sibling frontend's staging build environment. Backend credentials never belong in `NEXT_PUBLIC_*` values. Rebuild after setting the actual staging API origins.
- Review and pin the PostgreSQL, Redis, Python and official ClamAV images before host deployment. The first three reuse the existing deployment defaults; no image support/digest verification was performed here. The scanner reference must be supplied explicitly.
- Keep secrets in the host's secret store or protected environment file. Use generated URL-safe secrets without dollar-sign interpolation. The backup encryption key must be standard base64 encoding of 32 random bytes. Keep a protected recovery copy separate from the archives.

## 1. Offline preparation

Replace every example domain/credential. Set the API host in ALLOWED_HOSTS and the same HTTPS frontend origin in FRONTEND_URL, CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS. Set the proxy's actual trusted CIDRs once the host is chosen; never trust all networks. Configure passkey origins only for a real domain you control.

From the repository root, run the available Python interpreter:

```text
python deployment/check_staging.py --env .env.staging
```

This does not contact services, prove credentials or print their values. The supplied example intentionally fails. It checks the settings expected by this exact stack; adapt and review it if hosting uses managed services instead of the Compose database/cache.

On the eventual Docker host, validate Compose without displaying expanded credentials:

```text
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml config --quiet
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml build
```

Do not publish full `docker compose config` output; it contains expanded secrets. Never run `down --volumes` against an environment containing needed data.

## 2. Infrastructure and migration

```text
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml up -d db redis clamav
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml run --rm --no-deps backend python manage.py check --deploy
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml run --rm --no-deps backend python manage.py migrate --plan
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml run --rm --no-deps backend python manage.py migrate --noinput
```

Wait for database/cache readiness and scanner signature readiness; `service_started` is not a scanner readiness guarantee. The scanner shares a private scanning network with the backend and worker and has separate outbound access for signature updates. No database, Redis or scanner ports are published. Volumes are scoped to the explicit `smartbiz-staging` project; do not reuse a production project name or external production volumes.

Existing-data upgrades require a verified backup and migration review. A fresh staging installation should use synthetic records rather than a copy of customer data. Migration 0003 in records_management conservatively restricts historical record classification; earlier security migrations have additional upgrade requirements documented in [RUNBOOK.md](RUNBOOK.md).

## 3. Start and route the application

```text
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml up -d backend worker
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml run --rm backend python manage.py check_attachment_scanner --test-detection --test-upload-limit
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml run --rm backend python manage.py check_platform_services
docker compose --env-file .env.staging -p smartbiz-staging -f deployment/docker-compose.staging.yml up -d scheduler
```

Configure a same-host HTTPS reverse proxy to `127.0.0.1:18000`, preserving Host and setting the trusted forwarded protocol itself. Block direct public access to port 18000. This template does not include TLS certificates or a proxy. A containerized/managed proxy needs a reviewed private-network adaptation; do not solve routing by publishing the backend on all interfaces.

Deploy the separately built frontend at the configured HTTPS origin. Keep exactly one scheduler. Inspect web/worker/scheduler logs and confirm health evidence becomes fresh. The monitoring command authenticates SMTP and writes/deletes a storage probe; it does not prove inbox delivery or bucket privacy. Scanner failures must continue to reject uploads; never disable scan enforcement to make startup appear healthy.

## 4. Acceptance checklist — record actual evidence

| Check | Evidence required before approval |
| --- | --- |
| Clean install | Image/dependency versions, build output, migration plan and successful schema/application checks |
| Login and roles | Test admin, leader, manager, employee and platform sessions; OTP, refresh/logout and cross-company denials |
| Company setup | Headquarters, optional departments, leader assignment/access preview, invitation acceptance and scoped headcounts |
| Forms and requests | Library selection, published form entry, draft/file, submit/return/correct/approve, later pages and request requirements |
| Records | Supported issuance rule, appropriately authorized actor, full record creation, repeat action without duplicates, private-source denial |
| Storage and email | Private anonymous access denied, authenticated download works, actual messages arrive only at test inboxes |
| Scanner | Clean, detection and maximum-size probes pass; scanner outage rejects an isolated draft upload and leaves no stored file |
| Scheduled work | Worker responds, one scheduler runs, reporting/monitoring evidence updates without duplicate jobs |
| Device usability | Real phone and desktop; keyboard, light/dark theme, file picker, long forms, errors and browser Back/refresh warnings |
| Historical settings | Legacy classifications and unenforced field evidence switches reviewed; no unsupported evidence promises |

## 5. Restore and rollback exercise

Use `create_platform_backup` to produce a completed encrypted backup, with a protected persistent `/backups` destination. The stack mounts that destination into app/worker/scheduler services, but a same-host volume is not off-host backup protection.

Use `prepare_backup_restore --backup <completed-backup-directory> --output <new-recovery-directory>` to authenticate/decrypt an archive. Mount a protected, persistent recovery directory outside `/app` and `/backups` when running this in a disposable container; otherwise the prepared files disappear with that container. The output directory must be new. This command does not restore a database or certify a successful restore.

Restore the prepared database dump and file archive into a second, explicitly isolated database/bucket using the host's reviewed restore procedure. Verify counts, sample synthetic records, permissions and file integrity through the application. Record the successful exercise only after those checks. Do not execute a generic restore against a live connection or overwrite the running staging database as a shortcut.

Retain encrypted off-host backups and a separately protected key. Enable BACKUP_AUTOMATION_ENABLED only after restore, retention and destination checks pass. Test compatible app-version rollback; do not reverse destructive migrations automatically. Keep writers stopped during any database recovery.

## Current verification

Offline checks: 11 tests passed for configuration validation, placeholder rejection, insecure-setting rejection, network/port boundaries and staging-only env references. YAML parsed successfully. Docker/Compose expansion, image builds, TLS, credentials, scanner, SMTP, private storage, restore and device checks are **not yet verified**. No service was started and no production configuration was changed by preparing these files.
