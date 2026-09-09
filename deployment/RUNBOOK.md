# Production runbook baseline

## Before deploy
- Back up PostgreSQL and verify restore credentials.
- Confirm object-storage bucket is private and signed URLs expire quickly.
- Confirm Redis is not publicly reachable.
- Confirm secrets are supplied by the deployment secret store, never committed env files.
- Run backend checks, migrations plan, tests, OpenAPI validation, frontend typecheck/lint/build.
- Review pending migrations for locks/table rewrites and schedule maintenance where necessary.

## Deploy order
1. Apply backward-compatible database migrations.
2. Deploy backend web and workers.
3. Start scheduler only after web/worker health is green.
4. Deploy frontend using the same frozen API contract.
5. Smoke test login, refresh, `/users/me/`, company setup, one tenant workflow, private file download, support ticket, and platform control center.

## Rollback
- Roll back application containers first.
- Do not reverse destructive migrations automatically.
- Restore database only after confirming data-loss scope and stopping writers.
- Revoke compromised sessions/keys if the rollback is security-related.

## Backups
- Automated encrypted PostgreSQL backups with point-in-time recovery where supported.
- Versioned/private object storage with lifecycle retention appropriate to each classification.
- Perform recurring restore drills; an untested backup is not considered sufficient.

## Monitoring
Alert on elevated 5xx rates, login failures/lockouts, worker queue age, failed scheduled jobs, DB saturation, Redis failures, storage errors, malware scan failures, email queue failures, and security/audit pipeline failures.
