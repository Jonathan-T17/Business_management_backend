from django.core.management.base import BaseCommand
from django.utils import timezone

from reporting_schedules.models import (
    ReportingObligation,
)

from reporting_schedules.services import (
    ReportingObligationService,
)


class Command(BaseCommand):

    def handle(
        self,
        *args,
        **options,
    ):

        now = timezone.now()

        missed = (
            ReportingObligation.objects
            .filter(
                status__in=[
                    "PENDING",
                    "DRAFT",
                ],
                due_at__lt=now,
                submission__isnull=True,
            )
            .select_related(
                "schedule",
                "user",
                "company",
            )
        )

        count = missed.count()

        for obligation in missed:

            obligation.status = "MISSED"

            obligation.save(
                update_fields=[
                    "status",
                ]
            )

            ReportingObligationService.send_overdue_notification(
                obligation
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reviewed {count} "
                f"reporting obligations."
            )
        )