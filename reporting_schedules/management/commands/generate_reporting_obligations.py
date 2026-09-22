from django.core.management.base import BaseCommand
from django.utils import timezone
from companies.models import Company
from reporting_schedules.services import ReportingScheduleService


class Command(BaseCommand):
    help = "Generate obligations for each active company's current local date."

    def handle(self, *args, **options):
        now = timezone.now()
        total = 0
        for company in Company.objects.filter(is_active=True).iterator():
            total += len(ReportingScheduleService.generate_for_company_now(company=company, now=now))
        self.stdout.write(self.style.SUCCESS(f"Created {total} reporting obligations."))
