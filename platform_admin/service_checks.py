"""Explicit worker probes. Health page requests only read their saved results."""
from uuid import uuid4
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import get_connection
from django.core.mail.backends.smtp import EmailBackend
from .health import record_evidence


def check_email_connection():
    connection = get_connection(fail_silently=False)
    if not isinstance(connection, EmailBackend):
        record_evidence("email_connection", "not_monitored", "The configured email backend is not SMTP. Configure a real email provider before going online.")
        return
    try:
        connection.open()
        if connection.connection is None:
            raise RuntimeError("No SMTP connection")
        record_evidence("email_connection", "healthy", "Email server connection and configured authentication succeeded. This does not verify message or inbox delivery.")
    except Exception:
        record_evidence("email_connection", "unhealthy", "Cannot connect or authenticate to the email server. Check provider settings and network access.")
    finally:
        try:
            connection.close()
        except Exception:
            pass


def check_storage():
    name = None
    status = "healthy"
    detail = "A temporary file was written, read and removed successfully. This checks availability, not storage access policy or backups."
    try:
        payload = uuid4().hex.encode("ascii")
        name = default_storage.save(".healthchecks/" + uuid4().hex, ContentFile(payload))
        with default_storage.open(name, "rb") as probe:
            if probe.read(33) != payload:
                raise RuntimeError("Storage verification failed")
    except Exception:
        status = "unhealthy"
        detail = "File storage could not write or read its test file. Check storage configuration and access."
    finally:
        if name:
            try:
                default_storage.delete(name)
                if default_storage.exists(name):
                    raise RuntimeError("Cleanup incomplete")
            except Exception:
                status = "unhealthy"
                detail = "Storage test-file cleanup failed. Check storage delete permissions."
    record_evidence("storage", status, detail)


def run_service_checks():
    check_email_connection()
    check_storage()
