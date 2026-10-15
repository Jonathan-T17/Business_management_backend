from celery import shared_task
from .service_checks import run_service_checks


@shared_task
def monitor_services():
    run_service_checks()


@shared_task
def create_backup():
    from django.core.management import call_command
    call_command("create_platform_backup")
