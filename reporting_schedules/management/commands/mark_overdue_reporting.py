from django.core.management.base import BaseCommand
from reporting_schedules.services import ReportingObligationStateService


class Command(BaseCommand):
    help = "Mark unsubmitted obligations, including linked drafts, as missed."

    def handle(self, *args, **options):
        count = ReportingObligationStateService.mark_overdue()
        self.stdout.write(self.style.SUCCESS(f"Marked {count} reporting obligations missed."))
