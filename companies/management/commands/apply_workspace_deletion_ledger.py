"""Run against an isolated restored database BEFORE exposing it to users."""
import json
from pathlib import Path
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.exceptions import FieldDoesNotExist

from companies.models import Company, WorkspacePurgeReceipt
from companies.purge import file_identity
from companies.purge_inventory import DIRECT, CHILDREN
from django.apps import apps
from django.db import models
from security.services import create_audit_log, terminate_company_sessions


class Command(BaseCommand):
    help = "Block erased workspaces in an isolated restored database using the separate deletion ledger. Does not erase business data."

    def add_arguments(self, parser):
        parser.add_argument("--directory", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        directory = Path(options["directory"])
        if not directory.is_dir():
            raise CommandError("Choose the protected deletion ledger directory.")
        entries = []
        try:
            for path in directory.glob("*.json"):
                if path.stat().st_size > 32 * 1024 * 1024:
                    raise ValueError()
                data = json.loads(path.read_text(encoding="utf-8"))
                stamp = parse_datetime(data["deleted_at"])
                if data["version"] != 1 or type(data["workspace_id"]) is not int or data["workspace_id"] <= 0 or not stamp or timezone.is_naive(stamp):
                    raise ValueError()
                files = data.get("pending_files", [])
                if not isinstance(files, list) or len(files) > 100_000:
                    raise ValueError()
                for entry in files:
                    if entry["model"] not in DIRECT | set(CHILDREN) | {"companies.company"}:
                        raise ValueError()
                    field = apps.get_model(entry["model"])._meta.get_field(entry["field"])
                    if not isinstance(field, models.FileField):
                        raise ValueError()
                    file_identity(field, entry["name"])
                entries.append((UUID(data["receipt"]), data["workspace_id"], stamp, files))
        except (ValueError, KeyError, TypeError, OSError, LookupError, FieldDoesNotExist, AttributeError):
            raise CommandError("Invalid deletion ledger; nothing was applied.")
        # Validate the entire directory before touching any company.
        highest = 0
        for receipt_id, workspace_id, deleted_at, files in entries:
            highest = max(highest, workspace_id)
            receipt, created = WorkspacePurgeReceipt.objects.get_or_create(workspace_id=workspace_id, defaults={"id": receipt_id, "status": "BACKUP_BLOCKED"})
            if created:
                receipt.created_at = deleted_at
            receipt.pending_files = list({(entry["model"],entry["field"],entry["name"]):entry for entry in [*receipt.pending_files,*files]}.values())
            company = Company.objects.select_for_update().filter(pk=workspace_id).first()
            if company:
                now = timezone.now()
                company.is_active = False
                company.archived_at = now
                company.recovery_until = now
                company.active_before_archive = False
                company.archive_reason = "Recovery blocked by permanent deletion ledger."
                company.save(update_fields=("is_active", "archived_at", "recovery_until", "active_before_archive", "archive_reason"))
                receipt.status = "BACKUP_BLOCKED"
                terminate_company_sessions(company, reason="ACCOUNT_STATE", note="Deleted workspace found in restored backup")
                create_audit_log(company=company, action="DELETED_WORKSPACE_RESTORE_BLOCKED", severity="CRITICAL", description="Deletion ledger reapplied before restored database exposure.")
            elif created:
                receipt.status = "FILES_PENDING" if receipt.pending_files else "COMPLETE"
            receipt.save()
        # A restored sequence must not reassign a previously erased workspace ID.
        if highest and connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), GREATEST(%s, COALESCE((SELECT MAX(id) FROM companies_company), 1)), true)", [Company._meta.db_table, highest])
        self.stdout.write(self.style.SUCCESS(f"Applied {len(entries)} deletion markers. Restored erased workspaces remain inaccessible."))
