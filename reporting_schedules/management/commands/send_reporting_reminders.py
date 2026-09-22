from django.core.management.base import BaseCommand
from reporting_schedules.services import ReportingReminderService


class Command(BaseCommand):
    help = "Send in-app morning and final-hour reminders in each company's timezone."

    def handle(self, *args, **options):
        count = ReportingReminderService.send_pending()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} reporting reminders."))
