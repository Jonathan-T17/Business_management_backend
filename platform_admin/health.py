from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone


def check_database():

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {
            "status": "healthy"
        }

    except Exception:
        return {
            "status": "unhealthy"
        }


def check_cache():

    try:
        key = (
            "platform_health_check"
        )

        cache.set(
            key,
            "ok",
            timeout=10,
        )

        result = cache.get(key)

        return {
            "status": (
                "healthy"
                if result == "ok"
                else "unhealthy"
            )
        }

    except Exception:
        return {
            "status": "unhealthy"
        }


def check_email_configuration():

    backend = getattr(
        settings,
        "EMAIL_BACKEND",
        "",
    )

    return {
        "status": (
            "configured"
            if backend
            else "not_configured"
        ),
        "backend": backend,
    }


def record_evidence(service, status, detail):
    import logging
    from .models import ServiceHealthEvidence
    try:
        ServiceHealthEvidence.objects.update_or_create(
            service=service,
            defaults={"status": status, "checked_at": timezone.now(), "detail": detail},
        )
    except Exception:
        logging.getLogger(__name__).warning("Service monitoring evidence could not be saved: %s", service)


def evidence_health(service, max_age, missing):
    from .models import ServiceHealthEvidence
    try:
        result = ServiceHealthEvidence.objects.filter(service=service).first()
        if result:
            age = (timezone.now() - result.checked_at).total_seconds()
            fresh = 0 <= age < max_age
            return {"status": result.status if fresh else "unhealthy",
                    "last_run": result.checked_at.isoformat(),
                    "detail": result.detail if fresh else "The monitoring result is out of date. Check that the scheduled worker is running."}
    except Exception:
        return {"status": "not_monitored", "detail": "Monitoring evidence could not be read. Check the database and applied migrations."}
    return {"status": "not_monitored", "detail": missing}


def record_reporting_run(status):
    record_evidence("reporting", "healthy" if status == "SUCCESS" else "unhealthy",
                    "Last reporting run succeeded." if status == "SUCCESS" else "Reporting failed. Check the reporting worker logs.")


def reporting_health():
    return evidence_health("reporting", 180, "No reporting run has been recorded. Start the reporting worker and scheduler.")


def get_platform_health():
    database = check_database()
    cache_result = check_cache()
    services = {
        "database": database, "cache": cache_result,
        "email_delivery": evidence_health("email_connection", 900, "Run the service checks to verify the email server connection. Inbox delivery is not measured."),
        "reporting": reporting_health(),
        "storage": evidence_health("storage", 900, "Run the service checks to verify file storage."),
        "backups": backup_health(),
    }
    statuses = {service["status"] for service in services.values()}
    overall = "degraded" if "unhealthy" in statuses else "healthy" if statuses == {"healthy"} else "partially_monitored"
    return {"status": overall, "services": services, "database": database,
            "cache": cache_result, "email": check_email_configuration(), "timestamp": timezone.now()}


def backup_health():
    copy = evidence_health("backup_copy", 36 * 3600, "No completed backup is recorded. Configure a protected destination and encryption key, then schedule database and file backups.")
    if copy["status"] != "healthy":
        return copy
    return {"status": "not_monitored", "last_run": copy["last_run"],
            "detail": "An encrypted backup passed integrity checks. Recovery remains unverified until it is restored and tested in a separate environment."}
