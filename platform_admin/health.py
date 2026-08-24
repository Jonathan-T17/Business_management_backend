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


def get_platform_health():

    database = check_database()

    cache_result = check_cache()

    email = (
        check_email_configuration()
    )

    critical_healthy = (
        database["status"]
        == "healthy"
        and cache_result["status"]
        == "healthy"
    )

    return {
        "status": (
            "healthy"
            if critical_healthy
            else "degraded"
        ),

        "database": database,

        "cache": cache_result,

        "email": email,

        "timestamp":
            timezone.now(),
    }