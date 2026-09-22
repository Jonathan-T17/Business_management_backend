"""Periodic reporting maintenance; all operations can be safely repeated."""
from celery import shared_task
from django.core.management import call_command


@shared_task
def process_reporting():
    call_command("generate_reporting_obligations")
    call_command("mark_overdue_reporting")
    call_command("send_reporting_reminders")
