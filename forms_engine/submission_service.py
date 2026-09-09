from copy import deepcopy

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.data_classification import DataClassification
from core.sequence import CompanySequenceService, company_local_date


class FormSubmissionLifecycleService:
    EDITABLE = {"DRAFT", "RETURNED"}

    @classmethod
    def _assert_template_eligibility(cls, *, template, actor):
        if template.company_id != actor.company_id or template.lifecycle_status != "PUBLISHED" or not template.is_active:
            raise ValidationError("This form is not available.")
        profile = getattr(actor, "employee_profile", None)
        checks = (("branch_id", actor.branch_id), ("department_id", getattr(profile, "department_id", None)), ("team_id", getattr(profile, "team_id", None)))
        for field, actual in checks:
            expected = getattr(template, field, None)
            if expected and expected != actual:
                raise ValidationError("You are not eligible to use this form.")

    @classmethod
    @transaction.atomic
    def start(cls, *, template, actor, title="", project=None, task=None, obligation=None):
        from forms_engine.models import FormSubmission

        cls._assert_template_eligibility(template=template, actor=actor)
        if project and project.company_id != actor.company_id:
            raise ValidationError("Cross-company project denied.")
        if task and (task.company_id != actor.company_id or project and task.project_id != project.id):
            raise ValidationError("Invalid task context.")
        profile = getattr(actor, "employee_profile", None)
        schema = [
            {
                "key": field.key,
                "label": field.label,
                "field_type": field.field_type,
                "required": field.required,
                "options": deepcopy(field.options),
                "validation_rules": deepcopy(field.validation_rules),
                "classification": getattr(field, "classification", DataClassification.NORMAL),
                "order": field.order,
            }
            for field in template.fields.filter(is_active=True).order_by("order", "id")
        ]
        submission = FormSubmission.objects.create(
            company=actor.company,
            template=template,
            submitted_by=actor,
            branch=getattr(actor, "branch", None),
            department=getattr(profile, "department", None),
            team=getattr(profile, "team", None),
            project=project,
            task=task,
            title=title,
            reporting_date=company_local_date(actor.company),
            reference_number=CompanySequenceService.next(company=actor.company, prefix="FRM"),
            status="DRAFT",
            template_version=template.version,
            schema_snapshot=schema,
            data={},
        )
        if obligation:
            obligation.submission = submission
            obligation.status = "DRAFT"
            obligation.save(update_fields=["submission", "status"])
        return submission

    @classmethod
    @transaction.atomic
    def update_data(cls, *, submission, actor, data):
        from forms_engine.models import FormSubmission

        submission = FormSubmission.objects.select_for_update().get(pk=submission.pk)
        if submission.submitted_by_id != actor.id or submission.status not in cls.EDITABLE:
            raise ValidationError("Only the author may edit a draft or returned submission.")
        allowed = {field["key"] for field in submission.schema_snapshot}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError({"data": f"Unknown fields: {', '.join(sorted(unknown))}."})
        submission.data = data
        submission.save(update_fields=["data", "updated_at"])
        return submission

    @classmethod
    @transaction.atomic
    def submit(cls, *, submission, actor, request=None):
        from forms_engine.models import FormSubmission
        from workflows.runtime_service import WorkflowRuntimeService

        submission = FormSubmission.objects.select_for_update().select_related("template__workflow").get(pk=submission.pk)
        if submission.submitted_by_id != actor.id or submission.status not in cls.EDITABLE:
            raise ValidationError("This submission cannot be submitted.")
        for field in submission.schema_snapshot:
            if field["required"] and submission.data.get(field["key"]) in (None, "", []):
                raise ValidationError({field["key"]: "This field is required."})
        workflow = submission.template.workflow
        if not workflow or not workflow.is_active:
            raise ValidationError("No published approval route is configured for this form.")
        return WorkflowRuntimeService.start(workflow=workflow, target=submission, submitted_by=actor, request=request)


class FormSubmissionWorkflowAdapter:
    target_type = "FORM_SUBMISSION"

    @staticmethod
    def assert_submit_allowed(*, target, actor):
        if target.submitted_by_id != actor.id or target.status not in {"DRAFT", "RETURNED"}:
            raise ValidationError("Form submission cannot be submitted.")

    @staticmethod
    def assert_participant_review_allowed(*, target, actor, workflow_instance):
        if not workflow_instance.steps.filter(recipients__user=actor).exists():
            raise ValidationError("Workflow participation is required.")

    @staticmethod
    def on_submitted(*, target, actor, workflow_instance, request=None):
        target.status = "SUBMITTED"
        target.submitted_at = timezone.now()
        target.save(update_fields=["status", "submitted_at", "updated_at"])
        if hasattr(target, "reporting_obligation"):
            from reporting_schedules.services import ReportingObligationStateService
            ReportingObligationStateService.mark_submitted(obligation=target.reporting_obligation, submitted_at=target.submitted_at)

    @staticmethod
    def on_approved(*, target, actor, workflow_instance, request=None):
        target.status = "APPROVED"
        target.approved_at = timezone.now()
        target.save(update_fields=["status", "approved_at", "updated_at"])
        from records_management.finalizers import OfficialRecordFinalizer
        OfficialRecordFinalizer.maybe_issue(source=target, actor=actor, workflow_instance=workflow_instance, request=request)
