from datetime import timedelta
from unittest.mock import patch, MagicMock
import pytest
from django.test import override_settings
from django.core.files.storage import InMemoryStorage
from django.utils import timezone
from platform_admin.health import record_reporting_run, reporting_health, get_platform_health
from platform_admin.models import ServiceHealthEvidence
from platform_admin.service_checks import check_storage, check_email_connection

pytestmark = pytest.mark.django_db


def test_reporting_survives_cache_loss():
    from django.core.cache import cache
    record_reporting_run("SUCCESS")
    cache.clear()
    assert reporting_health()["status"] == "healthy"
    ServiceHealthEvidence.objects.update(checked_at=timezone.now()-timedelta(minutes=4))
    assert reporting_health()["status"] == "unhealthy"


def test_storage_roundtrip_cleans_up():
    storage = InMemoryStorage()
    with patch("platform_admin.service_checks.default_storage", storage):
        check_storage()
    assert ServiceHealthEvidence.objects.get(service="storage").status == "healthy"
    assert storage.listdir(".healthchecks")[1] == []


def test_storage_cleanup_failure_is_unhealthy():
    storage = InMemoryStorage()
    with patch("platform_admin.service_checks.default_storage", storage), patch.object(storage, "delete", side_effect=OSError):
        check_storage()
    assert ServiceHealthEvidence.objects.get(service="storage").status == "unhealthy"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_test_email_backend_is_not_live_email_evidence():
    check_email_connection()
    assert ServiceHealthEvidence.objects.get(service="email_connection").status == "not_monitored"


def test_email_probe_never_sends_messages():
    from django.core.mail.backends.smtp import EmailBackend
    connection = MagicMock(spec=EmailBackend)
    connection.connection = object()
    with patch("platform_admin.service_checks.get_connection", return_value=connection):
        check_email_connection()
    connection.send_messages.assert_not_called()
    connection.close.assert_called_once()
    assert ServiceHealthEvidence.objects.get(service="email_connection").status == "healthy"


def test_email_failure_is_degraded_and_sanitized():
    from django.core.mail.backends.smtp import EmailBackend
    connection = MagicMock(spec=EmailBackend)
    connection.open.side_effect = OSError("secret-provider-information")
    with patch("platform_admin.service_checks.get_connection", return_value=connection):
        check_email_connection()
    health = get_platform_health()
    assert health["status"] == "degraded"
    assert "secret-provider-information" not in str(health)
    assert health["services"]["backups"]["status"] == "not_monitored"
