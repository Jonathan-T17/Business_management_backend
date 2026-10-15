# Backup and recovery preparation

The backup commands are ready, but no live backup destination or encryption key
has been configured. No real company backup has been copied during implementation.

## Configure the destination

Choose a protected directory on a separate drive or backup server. It must already
exist, be outside the application checkout and uploaded-file tree, and allow only
the backup operator/worker. On Windows set the directory ACLs; on Linux restrict
ownership and permissions. For containers, mount that destination into the worker.
Do not use a container's ephemeral filesystem. Cloud storage requires a mounted
backup destination or a separate provider integration; this implementation does
not upload backup archives directly to an arbitrary cloud bucket.

Set BACKUP_DIRECTORY to that directory and BACKUP_ENCRYPTION_KEY to a base64-encoded
32-byte random key in the deployment secret store. Generate the key with a trusted
secret manager or Python secrets.token_bytes(32), then base64-encode it. Keep a
recoverable copy of the key separately from the backups. Do not reuse SECRET_KEY,
a password, or storage credentials as the backup key. Key rotation requires keeping
the old keys for older archives; the recovery command uses the selected key.

The configured uploaded-file storage must be a dedicated directory or the private
object store. A local default storage that points at the application checkout is
refused because it could capture application secrets and code. PostgreSQL pg_dump
must be installed and match or exceed the server version. The production image
now includes the distribution's PostgreSQL client; confirm compatibility with your
chosen server version during deployment.

## Create a backup

Run `python manage.py create_platform_backup`. It takes a consistent PostgreSQL
custom-format dump and a streaming archive of uploaded files, encrypting each
with AES-256-GCM. Database credentials are supplied to pg_dump through its process
environment rather than command arguments. Plain company data is not written to
temporary backup files. A completion marker is written only after both encrypted
archives authenticate. The health page records completion or failure.

Database and uploaded files are captured separately, so writes across the two
stores are not an atomic snapshot. For a coordinated recovery point, pause company
file/submission writers during the backup window or use coordinated infrastructure
snapshots. Hidden health-check objects are excluded. Symlinked storage paths and
paths escaping the uploaded-file directory are rejected.

To schedule daily copies in production, set BACKUP_AUTOMATION_ENABLED=True after
mounting the destination and configuring the key, then restart the worker and the
single scheduler. Backup runs use a database lock to prevent overlapping copies.
A failed run needs attention; evidence older than 36 hours is also flagged.
The local reporting runner does not automatically schedule backups.

Retention is not automatic in this first version: choose a retention policy and
check destination capacity. No old copies are deleted by these commands.

## Test recovery

Run `python manage.py prepare_backup_restore --backup <completed-backup-folder>
--output <new-protected-recovery-folder>` with the corresponding encryption key.
It authenticates both archives before writing decrypted recovery files and refuses
an existing output directory. The recovery directory contains confidential data:
restrict its access before running this command. The encrypted backup stays intact.

On a separate test server with separate credentials, use pg_restore to load
`database.dump` into a new empty test database. Extract `files.tar.gz` only into a
new isolated file store using safe extraction. Start an isolated application with
email delivery and background jobs disabled, then verify company records, form
submissions, file downloads and access boundaries. Never point the recovery
application at production Redis, SMTP, buckets, or the production database.

This preparation command does not perform a database restore or mark restore
success. Backup integrity and recovery are different checks. The overall backup
card remains unverified until a real restore drill and its monitoring integration
are completed. Do not infer recovery success from a completion marker or archive
integrity alone.
