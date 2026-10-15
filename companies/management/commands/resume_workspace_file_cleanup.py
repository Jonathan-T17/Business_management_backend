from django.core.management.base import BaseCommand
from companies.models import WorkspacePurgeReceipt
from companies.purge import resume_file_cleanup


class Command(BaseCommand):
    help = "Resume durable file cleanup for workspaces whose database records were already erased."

    def handle(self, *args, **options):
        pending = list(WorkspacePurgeReceipt.objects.filter(status="FILES_PENDING").values_list("pk", flat=True))
        complete = 0
        for pk in pending:
            complete += resume_file_cleanup(pk).status == "COMPLETE"
        self.stdout.write(f"Completed {complete} of {len(pending)} pending cleanup receipts.")
