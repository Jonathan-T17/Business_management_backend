import hashlib
import uuid
from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
@pytest.mark.postgres
def test_upgrade_preserves_existing_security_records_and_links():
    """Exercise a populated old schema in an isolated test-database schema."""
    schema = "migration_test_" + uuid.uuid4().hex
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute("SHOW search_path")
        original_path = cursor.fetchone()[0]
        cursor.execute(f"CREATE SCHEMA {quote(schema)}")
        cursor.execute(f"SET search_path TO {quote(schema)}")
    try:
        executor = MigrationExecutor(connection)
        legacy = [("security", "0003_alter_auditlog_object_id"), ("support", "0001_initial")]
        executor.migrate(legacy)
        old = executor.loader.project_state(legacy).apps
        company = old.get_model("companies", "Company").objects.create(name="Legacy")
        user = old.get_model("users", "User").objects.create(
            email="legacy@example.test", full_name="Legacy", company=company,
            is_active=True, email_verified=True,
        )
        session = old.get_model("security", "ActiveSession").objects.create(
            user=user, company=company, refresh_token_jti="legacy-jti", ip_address="127.0.0.1",
        )
        history = old.get_model("security", "LoginHistory").objects.create(
            user=user, company=company, session=session, ip_address="127.0.0.1",
        )
        old.get_model("security", "FailedLoginAttempt").objects.create(email=user.email, ip_address="127.0.0.1", attempts=3)
        for code in ("123456", "654321"):
            old.get_model("security", "OTP").objects.create(user=user, code=code, expires_at=timezone.now()+timedelta(minutes=5))
        old.get_model("security", "TrustedDevice").objects.create(user=user, fingerprint="old-browser", device_name="Legacy")
        ticket = old.get_model("support", "SupportTicket").objects.create(
            company=company, created_by=user, reference="LEGACY-1", subject="Legacy", description="Preserved",
        )
        old.get_model("support", "SupportMessage").objects.create(ticket=ticket, author=user, body="Preserved message")
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        current = executor.loader.project_state().apps
        migrated_history = current.get_model("security", "LoginHistory").objects.get(pk=uuid.UUID(int=history.pk))
        assert migrated_history.session_id == uuid.UUID(int=session.pk)
        assert migrated_history.email_hash == hashlib.sha256(user.email.encode()).hexdigest()
        assert current.get_model("security", "FailedLoginAttempt").objects.get().attempts == 3
        challenges = current.get_model("security", "OTP").objects.all()
        assert challenges.count() == 2
        assert challenges.filter(invalidated_at__isnull=True).count() == 0
        assert len(set(challenges.values_list("challenge_id", flat=True))) == 2
        assert not current.get_model("security", "TrustedDevice").objects.get().is_active
        assert current.get_model("support", "SupportMessage").objects.get().body == "Preserved message"
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('search_path', %s, false)", [original_path])
            cursor.execute(f"DROP SCHEMA {quote(schema)} CASCADE")
