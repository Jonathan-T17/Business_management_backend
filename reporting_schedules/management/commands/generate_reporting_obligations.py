from django.core.management.base import BaseCommand
from django.utils import timezone

from companies.models import Company

from reporting_schedules.services import (
    ReportingScheduleService,
)


class Command(BaseCommand):

    help = (
        "Generate reporting obligations "
        "for the current date."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        today = (
            timezone.localdate()
        )

        total = 0

        companies = (
            Company.objects.filter(
                is_active=True
            )
        )

        for company in companies:

            obligations = (
                ReportingScheduleService
                .generate_for_date(
                    company=company,
                    target_date=today,
                )
            )

            total += len(
                obligations
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {total} "
                f"reporting obligations."
            )
        )