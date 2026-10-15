"""Development runner for machines without a Celery broker."""
import logging
import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from reporting_schedules.tasks import process_reporting
from platform_admin.service_checks import run_service_checks

logger = logging.getLogger(__name__)
LOCK_ID = 738421905


class Command(BaseCommand):
    help = "Run reporting every minute and service probes every five minutes locally."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Use the production Celery worker and scheduler outside development.")
        if connection.vendor != "postgresql":
            raise CommandError("This runner requires PostgreSQL for duplicate-runner protection.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [LOCK_ID])
            acquired = cursor.fetchone()[0]
        if not acquired:
            raise CommandError("A local automation runner is already active.")
        self.stdout.write("Local automation started. Stop with Ctrl+C.")
        next_probe = 0
        try:
            while True:
                started = time.monotonic()
                try:
                    process_reporting()
                    self.stdout.write("Reporting cycle completed.")
                except Exception:
                    logger.exception("Reporting cycle failed; the next cycle will retry.")
                    if options["once"]:
                        raise CommandError("Reporting failed. Check the worker logs.")
                if started >= next_probe:
                    run_service_checks()
                    next_probe = time.monotonic() + 300
                    self.stdout.write("Service checks completed.")
                if options["once"]:
                    break
                time.sleep(max(0, 60 - (time.monotonic() - started)))
        except KeyboardInterrupt:
            self.stdout.write("Local automation stopped.")
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])
