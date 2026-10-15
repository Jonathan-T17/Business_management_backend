"""Reviewed workspace erasure, separate from ordinary business deletion.

Database erasure intentionally bypasses runtime PROTECT/immutability guards only
for an explicit ownership inventory. Every incoming relation is checked first;
PostgreSQL deferred constraints provide the final atomic boundary. Files are
removed after commit using a durable manifest, so failures can be resumed.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path, PurePosixPath

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.db import connection, models, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles
from security.services import create_audit_log
from .lifecycle import validate_confirmation
from .models import Company, WorkspacePurgeReceipt
from .purge_inventory import CHILDREN, DIRECT, RETAINED_COMPANY_MODELS


def require_owner(actor):
    if not CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN):
        raise PermissionDenied("Platform owner authority is required.")


def file_identity(field, name):
    """Only local unversioned storage is supported until adapters are reviewed."""
    storage = field.storage
    if not isinstance(storage, FileSystemStorage):
        raise ValueError("UNSUPPORTED_STORAGE")
    if not name or str(PurePosixPath(name)) != name or "\\" in name or ":" in name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
        raise ValueError("UNSAFE_FILE_NAME")
    base = Path(storage.location).resolve()
    resolved = Path(storage.path(name)).resolve()
    if not resolved.is_relative_to(base) or resolved == base or resolved != base / name:
        raise ValueError("UNSAFE_FILE_NAME")
    return str(resolved).casefold()


def ledger_directory():
    configured = getattr(settings, "WORKSPACE_PURGE_LEDGER_DIR", "")
    if not configured or not Path(configured).is_absolute():
        raise ValueError("LEDGER_NOT_CONFIGURED")
    directory = Path(configured).resolve()
    if not directory.is_dir():
        raise ValueError("LEDGER_NOT_CONFIGURED")
    for protected in (settings.MEDIA_ROOT, getattr(settings, "BACKUP_DIRECTORY", "")):
        if protected and directory.is_relative_to(Path(protected).resolve()):
            raise ValueError("LEDGER_MUST_BE_SEPARATE")
    return directory


def write_deletion_marker(receipt):
    directory = ledger_directory()
    payload = json.dumps({"version": 1, "workspace_id": receipt.workspace_id,
        "receipt": str(receipt.pk), "deleted_at": receipt.created_at.isoformat(),
        "pending_files": receipt.pending_files}, sort_keys=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as output:
            temporary = output.name
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, directory / f"{receipt.pk}.json")
        temporary = None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


class PurgePlan:
    MAX_ROWS = 100_000

    def __init__(self, company):
        self.company = company
        self.rows = {}
        self.files = []
        self.blockers = []
        self.members = list(company.users.order_by("pk").values_list("pk", flat=True)[:self.MAX_ROWS + 1])
        if len(self.members) > self.MAX_ROWS:
            self.blockers.append("This workspace requires a reviewed large-data deletion process.")
        if company.users.filter(models.Q(is_superuser=True) | models.Q(role=Roles.SUPERUSER)).exists():
            self.blockers.append("A platform identity is linked to this company; repair the membership before deletion.")
        if not company.archived_at or company.is_active:
            self.blockers.append("Archive the workspace before permanent deletion.")
        if not company.recovery_until or company.recovery_until > timezone.now():
            self.blockers.append("The 30-day recovery period has not ended.")
        if company.deletion_hold_reason:
            self.blockers.append("A retention hold prevents permanent deletion.")
        if apps.get_model("chat.Message").objects.filter(conversation__company=company).exclude(attachment_url="").exists():
            self.blockers.append("Legacy message attachments require storage review before deletion.")
        if not getattr(settings, "WORKSPACE_PURGE_ENABLED", False):
            self.blockers.append("Permanent deletion is disabled in this deployment.")
        self.backup_days = getattr(settings, "WORKSPACE_PURGE_BACKUP_RETENTION_DAYS", 0)
        if not isinstance(self.backup_days, int) or self.backup_days <= 0:
            self.blockers.append("Configure and verify backup retention before enabling permanent deletion.")
        if connection.vendor != "postgresql":
            self.blockers.append("The reviewed deletion transaction requires PostgreSQL.")
        try:
            ledger_directory()
        except ValueError:
            self.blockers.append("Configure a separate durable deletion ledger before enabling permanent deletion.")
        inventory = {label: "company_id" for label in DIRECT}
        inventory.update(CHILDREN)
        inventory["companies.company"] = "pk"
        for model in apps.get_models(include_auto_created=True):
            label = model._meta.label_lower
            company_field = next((f for f in model._meta.local_fields if f.name == "company" and f.is_relation and f.related_model is Company), None)
            if company_field and label not in DIRECT | RETAINED_COMPANY_MODELS | {"users.user"}:
                self.blockers.append("The workspace data inventory needs review before deletion.")
        total = 0
        for label, path in inventory.items():
            model = apps.get_model(label)
            pks = list(model._base_manager.filter(**{path: company.pk}).order_by("pk").values_list("pk", flat=True)[:self.MAX_ROWS + 1])
            total += len(pks)
            self.rows[model] = pks
            if total > self.MAX_ROWS:
                self.blockers.append("This workspace requires a reviewed large-data deletion process.")
                break
        if total <= self.MAX_ROWS:
            self._check_relations()
            self._collect_files()
        self.blockers = list(dict.fromkeys(self.blockers))
        payload = {
            "workspace": company.pk,
            "archived_at": str(company.archived_at), "recovery_until": str(company.recovery_until),
            "hold": company.deletion_hold_reason,
            "members": sorted(map(str, self.members)),
            "rows": {m._meta.label_lower: sorted(map(str, pks)) for m, pks in self.rows.items()},
            "files": self.files,
        }
        self.fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def _check_relations(self):
        all_models = list(apps.get_models(include_auto_created=True))
        for source in all_models:
            owned = self.rows.get(source, [])
            for field in source._meta.local_fields:
                if not field.is_relation or field.related_model not in self.rows:
                    continue
                target_ids = self.rows[field.related_model]
                if not target_ids:
                    continue
                outsiders = source._base_manager.filter(**{field.attname + "__in": target_ids}).exclude(pk__in=owned)
                if source._meta.label_lower == "users.user" and field.name in {"company", "branch"}:
                    outsiders = outsiders.exclude(pk__in=self.members)
                if outsiders.exists():
                    self.blockers.append("Records outside this workspace refer to its data. Resolve retention or cross-company references before deletion.")
            for generic in source._meta.private_fields:
                if not isinstance(generic, GenericForeignKey):
                    continue
                for target, pks in self.rows.items():
                    if not pks or target._meta.auto_created:
                        continue
                    ct = ContentType.objects.filter(app_label=target._meta.app_label, model=target._meta.model_name).first()
                    if ct and source._base_manager.filter(**{generic.ct_field + "_id": ct.pk, generic.fk_field + "__in": list(map(str, pks))}).exclude(pk__in=owned).exists():
                        self.blockers.append("A record outside this workspace refers to its content. Resolve that reference before deletion.")

    def _collect_files(self):
        identities = {}
        for model, pks in self.rows.items():
            if not pks:
                continue
            for field in model._meta.local_fields:
                if not isinstance(field, models.FileField):
                    continue
                for name in model._base_manager.filter(pk__in=pks).values_list(field.name, flat=True):
                    if not name:
                        continue
                    try:
                        identity = file_identity(field, name)
                    except ValueError:
                        self.blockers.append("File storage or a file path requires a reviewed deletion adapter.")
                        continue
                    identities[identity] = True
                    self.files.append({"model": model._meta.label_lower, "field": field.name, "name": name})
        # A file may have multiple database references. Never erase another tenant's file.
        names = {entry["name"] for entry in self.files}
        if names:
            for model in apps.get_models():
                for field in model._meta.local_fields:
                    if not isinstance(field, models.FileField):
                        continue
                    for pk, name in model._base_manager.filter(**{field.name + "__in": names}).values_list("pk", field.name):
                        try:
                            shared = file_identity(field, name) in identities
                        except ValueError:
                            shared = False
                        if shared and pk not in self.rows.get(model, []):
                            self.blockers.append("A file is shared with a retained identity or another workspace. Resolve its ownership before deletion.")
        self.files.sort(key=lambda item: (item["model"], item["field"], item["name"]))

    def summary(self):
        return {
            "fingerprint": self.fingerprint, "eligible": not self.blockers,
            "blockers": self.blockers, "recovery_until": self.company.recovery_until,
            "hold_reason": self.company.deletion_hold_reason,
            "records": {m._meta.label_lower: len(pks) for m, pks in self.rows.items() if pks},
            "files_count": len(self.files), "accounts_to_detach": len(self.members),
            "backup_retention_days": self.backup_days,
        }


def preview_purge(*, company, actor):
    require_owner(actor)
    return PurgePlan(company).summary()


def purge_workspace(*, company, actor, values, fingerprint, acknowledge_backups, request=None):
    require_owner(actor)
    if connection.in_atomic_block:
        raise ValidationError("Permanent deletion must run outside an enclosing transaction.")
    if not acknowledge_backups:
        raise ValidationError("Acknowledge the backup retention policy before deletion.")
    # No files are touched until this transaction successfully commits.
    with transaction.atomic():
        company = Company.objects.select_for_update().get(pk=company.pk)
        validate_confirmation(actor, company, values)
        plan = PurgePlan(company)
        if plan.blockers:
            raise ValidationError({"detail": "Permanent deletion is blocked.", "blockers": plan.blockers})
        if fingerprint != plan.fingerprint:
            raise ValidationError("The workspace changed. Review a fresh deletion preview.")
        receipt, created = WorkspacePurgeReceipt.objects.get_or_create(workspace_id=company.pk, defaults={"actor": actor})
        if not created and receipt.status != "BACKUP_BLOCKED":
            raise ValidationError("A deletion receipt already exists. Review the recovery ledger before continuing.")
        receipt.actor = actor
        receipt.status = "FILES_PENDING"
        receipt.counts = {m._meta.label_lower: len(pks) for m, pks in plan.rows.items() if pks}
        # A restored backup may predate uploads still awaiting cleanup. Preserve
        # their separately retained manifest alongside the restored database files.
        receipt.pending_files = list({(entry["model"], entry["field"], entry["name"]): entry
            for entry in [*receipt.pending_files, *plan.files]}.values())
        receipt.completed_at = None
        receipt.failure_code = ""
        receipt.save()
        from users.models import User
        from security.models import ActiveSession, OTP, TrustedDevice
        now = timezone.now()
        ActiveSession.objects.filter(user_id__in=plan.members).update(is_active=False, terminated_at=now)
        OTP.objects.filter(user_id__in=plan.members, invalidated_at__isnull=True).update(invalidated_at=now)
        TrustedDevice.objects.filter(user_id__in=plan.members).update(is_active=False, revoked_at=now)
        User.objects.filter(pk__in=plan.members).update(company=None, branch=None, is_active=False,
            account_state="DEACTIVATED", role=Roles.INDIVIDUAL)
        # PostgreSQL defers the FK constraints until commit. The complete reviewed
        # set can therefore be erased atomically, including PROTECT cycles, without
        # ever following cascades into an unreviewed or cross-company row.
        for model, pks in plan.rows.items():
            if pks:
                model._base_manager.filter(pk__in=pks)._raw_delete(using=connection.alias)
        # Enforce deferred constraints now; failures roll back the receipt and all rows.
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        create_audit_log(user=actor, request=request, action="WORKSPACE_DATABASE_PURGED", severity="CRITICAL",
            description=values["reason"],
            metadata={"workspace_id": receipt.workspace_id, "receipt": str(receipt.pk)})
    resume_file_cleanup(receipt.pk, actor=actor, request=request)
    return WorkspacePurgeReceipt.objects.get(pk=receipt.pk)


def resume_file_cleanup(receipt_id, *, actor=None, request=None):
    """Idempotent and serialized; exceptions retain a durable retry manifest."""
    if actor is not None:
        require_owner(actor)
    if connection.in_atomic_block:
        raise ValidationError("File cleanup must run outside an enclosing transaction.")
    with transaction.atomic():
        receipt = WorkspacePurgeReceipt.objects.select_for_update().get(pk=receipt_id)
        if receipt.status != "FILES_PENDING":
            return receipt
        if Company.objects.filter(pk=receipt.workspace_id).exists():
            receipt.failure_code = "WORKSPACE_PRESENT"
            receipt.save(update_fields=("failure_code",))
            return receipt
        try:
            write_deletion_marker(receipt)
        except Exception:
            receipt.failure_code = "DELETION_LEDGER_UNAVAILABLE"
            receipt.save(update_fields=("failure_code",))
            return receipt
        remaining = []
        for entry in receipt.pending_files:
            field = apps.get_model(entry["model"])._meta.get_field(entry["field"])
            try:
                identity = file_identity(field, entry["name"])
                # Recheck global references after commit and on every retry.
                for model in apps.get_models():
                    for candidate in model._meta.local_fields:
                        if isinstance(candidate, models.FileField):
                            for name in model._base_manager.filter(**{candidate.name: entry["name"]}).values_list(candidate.name, flat=True):
                                if file_identity(candidate, name) == identity:
                                    raise ValueError("FILE_REFERENCED")
                field.storage.delete(entry["name"])
                if field.storage.exists(entry["name"]):
                    raise ValueError("FILE_STILL_PRESENT")
            except Exception:
                # Never persist storage exception text: it may contain credentials.
                remaining.append(entry)
        receipt.pending_files = remaining
        receipt.failure_code = "FILE_CLEANUP_REQUIRED" if remaining else ""
        if not remaining:
            receipt.status = "COMPLETE"
            receipt.completed_at = timezone.now()
            create_audit_log(user=actor, request=request, action="WORKSPACE_LIVE_PURGE_COMPLETED", severity="CRITICAL",
                description="Workspace live database and referenced local files removed. Backup retention is separate.",
                metadata={"workspace_id": receipt.workspace_id, "receipt": str(receipt.pk)})
        receipt.save(update_fields=("pending_files", "failure_code", "status", "completed_at"))
        # If this rewrite fails, the earlier durable marker retains the full
        # manifest; retrying already removed files is safe and idempotent.
        try:
            write_deletion_marker(receipt)
        except Exception:
            pass
        return receipt
