from django.core.management.base import BaseCommand
from platform_admin.service_checks import run_service_checks
from platform_admin.health import get_platform_health


class Command(BaseCommand):
    help = "Verify SMTP connectivity and storage availability without sending email."

    def handle(self, *args, **options):
        run_service_checks()
        for name, result in get_platform_health()["services"].items():
            self.stdout.write(f"{name}: {result['status']} â€” {result.get('detail', '')}")
