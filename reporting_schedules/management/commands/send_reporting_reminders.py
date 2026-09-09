from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from reporting_schedules.models import (
    ReportingObligation,
)

from reporting_schedules.services import (
    ReportingObligationService,
)


class Command(BaseCommand):

    help = (
        "Send morning and one-hour-before-deadline "
        "reminders for pending reporting obligations."
    )

    def handle(
        self,
        *args,
        **options,
    ):

        now = timezone.now()
        today = timezone.localdate()

        pending = (
            ReportingObligation.objects
            .filter(
                status__in=[
                    "PENDING",
                    "DRAFT",
                ],
                reporting_date=today,
            )
            .select_related(
                "schedule",
                "user",
                "company",
            )
        )

        morning_count = 0
        final_count = 0

        for obligation in pending:

            if not obligation.morning_reminder_sent:
                ReportingObligationService.send_morning_reminder(
                    obligation
                )
                morning_count += 1

            if (
                not obligation.final_reminder_sent
                and obligation.due_at > now
                and obligation.due_at - now
                    <= timedelta(hours=1)
            ):
                ReportingObligationService.send_final_reminder(
                    obligation
                )
                final_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {morning_count} morning reminders "
                f"and {final_count} final reminders."
            )
        )
