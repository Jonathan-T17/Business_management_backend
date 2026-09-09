from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from core.data_classification import DataClassification
from security.services import create_audit_log
from .models import OfficialRecord, RecordSequence


class RecordNumberService:
    @staticmethod
    @transaction.atomic
    def next_number(*, company, prefix):
        year = timezone.localdate().year
        sequence, _ = RecordSequence.objects.select_for_update().get_or_create(company=company, prefix=prefix, year=year)
        sequence.last_number += 1
        sequence.save(update_fields=["last_number"])
        return f"{prefix}-{year}-{sequence.last_number:06d}"


class OfficialRecordService:
    PREFIXES = {"REPORT": "RPT", "REQUEST": "REQ", "FORM_SUBMISSION": "FRM", "PLAN": "PLN", "FIELD_SUMMARY": "FLD", "OTHER": "REC"}

    @classmethod
    def issue_if_configured(cls, *, source, record_type, status, actor, title, snapshot, approval_snapshot, branch=None, request=None, prefix=None, classification=DataClassification.NORMAL, source_version=1):
        from company_setup.models import OfficialRecordPolicy
        policy = OfficialRecordPolicy.objects.filter(company=source.company, source_type=record_type, trigger_status=status, automatic_issue=True, is_active=True).first()
        if not policy:
            return None
        return cls.issue(source=source, record_type=record_type, title=title, snapshot=snapshot, approval_snapshot=approval_snapshot, actor=actor, branch=branch, request=request, prefix=prefix or policy.prefix, classification=classification, source_version=source_version)

    @classmethod
    @transaction.atomic
    def issue(cls, *, source, record_type, title, snapshot, approval_snapshot, actor, branch=None, request=None, supersedes=None, prefix=None, classification=DataClassification.NORMAL, source_version=1):
        company = source.company
        if actor.company_id != company.id:
            raise PermissionDenied("Tenant record issuance requires company membership.")
        if not CapabilityService.has(actor, getattr(Capabilities, "ISSUE_OFFICIAL_RECORDS", "ISSUE_OFFICIAL_RECORDS")):
            raise PermissionDenied("Official record issuance denied.")
        content_type = ContentType.objects.get_for_model(source, for_concrete_model=False)
        existing = OfficialRecord.objects.select_for_update().filter(company=company, content_type=content_type, object_id=str(source.pk), source_version=source_version, status="ACTIVE").first()
        if existing and supersedes is None:
            return existing
        prefix = (prefix or cls.PREFIXES.get(record_type, cls.PREFIXES["OTHER"])).strip().upper()
        if not prefix or len(prefix) > 30 or not prefix.replace("-", "").isalnum():
            raise ValidationError("Invalid record prefix.")
        number = RecordNumberService.next_number(company=company, prefix=prefix)
        record = OfficialRecord.objects.create(
            company=company, branch=branch, record_type=record_type, record_number=number,
            title=title, content_type=content_type, object_id=str(source.pk), source_version=source_version,
            snapshot=snapshot, approval_snapshot=approval_snapshot, issued_at=timezone.now(), issued_by=actor,
            supersedes=supersedes, classification=classification,
        )
        if supersedes:
            supersedes.status = "SUPERSEDED"
            supersedes.save(update_fields=["status"])
        create_audit_log(user=actor, company=company, branch=branch, request=request, action="CREATE", description=f"Official record issued: {number}.", obj=record)
        return record

    @classmethod
    @transaction.atomic
    def void(cls, *, record, actor, reason, request=None):
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("A reason is required to void an official record.")
        record = OfficialRecord.objects.select_for_update().get(pk=record.pk)
        if actor.company_id != record.company_id or not CapabilityService.has(actor, Capabilities.VOID_OFFICIAL_RECORDS):
            raise PermissionDenied("Official record voiding denied.")
        if record.status != "ACTIVE":
            raise ValidationError("Only active official records can be voided.")
        record.status = "VOID"
        record.void_reason = reason
        record.voided_at = timezone.now()
        record.voided_by = actor
        record.save(update_fields=["status", "void_reason", "voided_at", "voided_by"])
        create_audit_log(user=actor, company=record.company, branch=record.branch, request=request, action="UPDATE", description=f"Official record voided: {record.record_number}.", obj=record, metadata={"reason": reason})
        return record

    @classmethod
    def correct(cls, *, record, snapshot, approval_snapshot, actor, reason, title=None, request=None):
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("A correction reason is required.")
        if record.status != "ACTIVE":
            raise ValidationError("Only active official records can be corrected.")
        corrected = cls.issue(source=record.source_object, record_type=record.record_type, title=title or record.title, snapshot=snapshot, approval_snapshot=approval_snapshot, actor=actor, branch=record.branch, request=request, supersedes=record, classification=record.classification, source_version=record.source_version + 1)
        if hasattr(corrected, "correction_reason"):
            corrected.correction_reason = reason
            corrected.save(update_fields=["correction_reason"])
        return corrected
