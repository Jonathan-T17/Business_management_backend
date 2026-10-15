"""Periodic reporting maintenance; all operations can be safely repeated."""
from celery import shared_task
from django.core.management import call_command


@shared_task
def process_reporting():
    from platform_admin.health import record_reporting_run
    try:
        call_command("generate_reporting_obligations")
        call_command("mark_overdue_reporting")
        call_command("send_reporting_reminders")
    except Exception:
        record_reporting_run("FAILED")
        raise
    record_reporting_run("SUCCESS")
