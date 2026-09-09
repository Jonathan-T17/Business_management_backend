from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.data_classification import DataClassification
from core.sequence import CompanySequenceService, company_local_date
from core.visibility import VisibilityService


class ReportLifecycleService:
    EDITABLE = {"DRAFT", "RETURNED"}

    @classmethod
    @transaction.atomic
    def create(cls, *, actor, validated_data, fields_data=()):
        from reports.models import Report, ReportField

        project = validated_data.get("project")
        if project and project.company_id != actor.company_id:
            raise ValidationError("Cross-company project denied.")
        report = Report.objects.create(
            company=actor.company,
            created_by=actor,
            status="DRAFT",
            reporting_date=company_local_date(actor.company),
            report_number=CompanySequenceService.next(company=actor.company, prefix="RPT"),
            **validated_data,
        )
        for item in fields_data:
            ReportField.objects.create(report=report, **item)
        return report

    @classmethod
    @transaction.atomic
    def update(cls, *, report, actor, validated_data, fields_data=None):
        from reports.models import Report, ReportField

        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.created_by_id != actor.id:
            raise ValidationError("Only the report author can edit this report.")
        if report.status not in cls.EDITABLE:
            raise ValidationError("Submitted or finalized reports cannot be edited.")
        for immutable in ("company", "created_by", "status", "report_number", "submitted_at", "approved_at"):
            validated_data.pop(immutable, None)
        for field, value in validated_data.items():
            setattr(report, field, value)
        report.save()
        if fields_data is not None:
            ReportField.objects.filter(report=report).delete()
            for item in fields_data:
                ReportField.objects.create(report=report, **item)
        return report

    @classmethod
    @transaction.atomic
    def submit(cls, *, report, actor, request=None):
        from reports.models import Report
        from reports.routing import ReportRoutingService
        from workflows.runtime_service import WorkflowRuntimeService

        report = Report.objects.select_for_update().get(pk=report.pk)
        if report.created_by_id != actor.id or report.status not in cls.EDITABLE:
            raise ValidationError("This report cannot be submitted by this user.")
        workflow = ReportRoutingService.resolve(report=report, actor=actor)
        return WorkflowRuntimeService.start(workflow=workflow, target=report, submitted_by=actor, request=request)

    @staticmethod
    def safe_for_secondary_processing(report):
        if getattr(report, "sensitivity", DataClassification.NORMAL) in DataClassification.NEVER_SECONDARY_PROCESSING:
            return False
        return report.visibility != "PRIVATE"


class ReportWorkflowAdapter:
    target_type = "REPORT"

    @staticmethod
    def assert_submit_allowed(*, target, actor):
        if target.created_by_id != actor.id or target.status not in {"DRAFT", "RETURNED"}:
            raise ValidationError("Report cannot be submitted.")

    @staticmethod
    def assert_participant_review_allowed(*, target, actor, workflow_instance):
        if not workflow_instance.steps.filter(recipients__user=actor).exists():
            raise ValidationError("Workflow participation is required.")

    @staticmethod
    def on_submitted(*, target, actor, workflow_instance, request=None):
        target.status = "SUBMITTED"
        target.submitted_at = timezone.now()
        target.save(update_fields=["status", "submitted_at", "updated_at"])

    @staticmethod
    def on_approved(*, target, actor, workflow_instance, request=None):
        target.status = "APPROVED"
        target.approved_at = timezone.now()
        target.save(update_fields=["status", "approved_at", "updated_at"])
        from records_management.finalizers import OfficialRecordFinalizer
        OfficialRecordFinalizer.maybe_issue(source=target, actor=actor, workflow_instance=workflow_instance, request=request)
