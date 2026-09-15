"""Data-preserving helpers for the legacy PostgreSQL security schema upgrade."""
import hashlib
import uuid

from django.utils import timezone


def _convert_legacy_ids(schema_editor, tables):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("This legacy ID migration requires PostgreSQL.")
    quote = schema_editor.quote_name
    with schema_editor.connection.cursor() as cursor:
        references = []
        for table in tables:
            cursor.execute("""
                SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid),
                       (SELECT attname FROM pg_attribute
                        WHERE attrelid=conrelid AND attnum=conkey[1])
                FROM pg_constraint WHERE contype='f' AND confrelid=%s::regclass
            """, [table])
            references.extend(cursor.fetchall())
        for table, name, definition, column in references:
            cursor.execute(f"ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(name)}")
        columns = {(table, "id") for table in tables}
        columns.update((table, column) for table, _, _, column in references)
        for table, column in sorted(columns):
            cursor.execute(f"ALTER TABLE {quote(table)} ALTER COLUMN {quote(column)} DROP IDENTITY IF EXISTS")
            cursor.execute(f"ALTER TABLE {quote(table)} ALTER COLUMN {quote(column)} DROP DEFAULT")
            cursor.execute(f"ALTER TABLE {quote(table)} ALTER COLUMN {quote(column)} TYPE uuid "
                           f"USING lpad(to_hex({quote(column)}), 32, '0')::uuid")
        for table, name, definition, column in references:
            cursor.execute(f"ALTER TABLE {quote(table)} ADD CONSTRAINT {quote(name)} {definition}")


def convert_security_ids(apps, schema_editor):
    _convert_legacy_ids(schema_editor, ["security_activesession", "security_auditlog",
                                       "security_loginhistory", "security_otp", "security_trusteddevice"])


def convert_support_message_ids(apps, schema_editor):
    _convert_legacy_ids(schema_editor, ["support_supportmessage"])


def backfill_security(apps, schema_editor):
    alias = schema_editor.connection.alias
    attempts = apps.get_model("security", "FailedLoginAttempt")
    for row in attempts.objects.using(alias).all().iterator():
        row.email_hash = hashlib.sha256(row.email.strip().lower().encode()).hexdigest()
        row.email_hint = row.email[:2] + "***"
        row.save(using=alias, update_fields=["email_hash", "email_hint"])
    for row in apps.get_model("security", "LoginHistory").objects.using(alias).select_related("user").iterator():
        if row.user_id:
            row.email_hash = hashlib.sha256(row.user.email.strip().lower().encode()).hexdigest()
            row.save(using=alias, update_fields=["email_hash"])
    for row in apps.get_model("security", "OTP").objects.using(alias).all().iterator():
        row.challenge_id = uuid.uuid4()
        row.code_digest = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        row.invalidated_at = timezone.now()
        row.save(using=alias, update_fields=["challenge_id", "code_digest", "invalidated_at"])
    for row in apps.get_model("security", "TrustedDevice").objects.using(alias).all().iterator():
        row.token_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        row.is_active = False
        row.revoked_at = timezone.now()
        row.save(using=alias, update_fields=["token_hash", "is_active", "revoked_at"])
    # Flush deferred FK checks before the following schema alterations.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


def backfill_account_states(apps, schema_editor):
    users = apps.get_model("users", "User").objects.using(schema_editor.connection.alias)
    users.filter(is_active=True).update(account_state="ACTIVE")
    users.filter(is_active=False, email_verified=True).update(account_state="DEACTIVATED")
    users.filter(is_deleted=True).update(account_state="TERMINATED")
