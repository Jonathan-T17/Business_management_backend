from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.sequence import CompanySequenceService


class BusinessRequestLifecycleService:
    EDITABLE = {"DRAFT", "RETURNED"}

    @staticmethod
    def resolve_definition(request_obj):
        from company_setup.models import RequestTypeDefinition

        definition = getattr(request_obj, "request_type_definition", None)
        if definition:
            return definition
        return RequestTypeDefinition.objects.filter(
            company=request_obj.company,
            code__iexact=request_obj.request_type,
            is_active=True,
        ).first()

    @classmethod
    def validate_definition(cls, request_obj):
        from documents.models import Attachment
        from django.contrib.contenttypes.models import ContentType

        definition = cls.resolve_definition(request_obj)
        if not definition:
            raise ValidationError("This request type is not configured or is inactive.")
        for field in ("amount", "quantity", "needed_by"):
            enabled = getattr(definition, f"{field}_enabled")
            required = getattr(definition, f"{field}_required")
            value = getattr(request_obj, field)
            if required and value is None:
                raise ValidationError({field: "This field is required for the selected request type."})
            if not enabled and value is not None:
                raise ValidationError({field: "This field is not enabled for the selected request type."})
        ct = ContentType.objects.get_for_model(request_obj)
        attachment_count = Attachment.objects.filter(company=request_obj.company, content_type=ct, object_id=str(request_obj.pk), is_active=True).count()
        if definition.attachments_required and not attachment_count:
            raise ValidationError("An attachment is required for this request type.")
        if not definition.attachments_allowed and attachment_count:
            raise ValidationError("Attachments are not allowed for this request type.")
        return definition

    @classmethod
    @transaction.atomic
    def create(cls, *, actor, definition, data):
        from requests_app.models import BusinessRequest

        if definition.company_id != actor.company_id or not definition.is_active:
            raise ValidationError("Invalid request type.")
        data.pop("workflow", None)
        data.pop("status", None)
        request_obj = BusinessRequest.objects.create(
            company=actor.company,
            requester=actor,
            request_type=definition.code,
            request_type_definition=definition,
            request_type_snapshot={
                "code": definition.code,
                "name": definition.name,
                "classification": getattr(definition, "classification", "NORMAL"),
            },
            workflow=definition.workflow,
            request_number=CompanySequenceService.next(company=actor.company, prefix="REQ"),
            currency=data.pop("currency", None) or actor.company.default_currency,
            status="DRAFT",
            **data,
        )
        return request_obj

    @classmethod
    @transaction.atomic
    def update(cls, *, request_obj, actor, data):
        from requests_app.models import BusinessRequest

        request_obj = BusinessRequest.objects.select_for_update().get(pk=request_obj.pk)
        if request_obj.requester_id != actor.id or request_obj.status not in cls.EDITABLE:
            raise ValidationError("Only the requester may edit a draft or returned request.")
        for immutable in ("company", "requester", "request_number", "request_type", "request_type_definition", "workflow", "status", "submitted_at", "approved_at", "fulfilled_at"):
            data.pop(immutable, None)
        for field, value in data.items():
            setattr(request_obj, field, value)
        request_obj.save()
        return request_obj

    @classmethod
    @transaction.atomic
    def submit(cls, *, request_obj, actor, request=None):
        from requests_app.models import BusinessRequest
        from workflows.runtime_service import WorkflowRuntimeService

        request_obj = BusinessRequest.objects.select_for_update().select_related("workflow").get(pk=request_obj.pk)
        if request_obj.requester_id != actor.id or request_obj.status not in cls.EDITABLE:
            raise ValidationError("This request cannot be submitted.")
        definition = cls.validate_definition(request_obj)
        workflow = definition.workflow
        if not workflow or not workflow.is_active or getattr(workflow, "lifecycle_status", "PUBLISHED") != "PUBLISHED":
            raise ValidationError("No published approval route is configured for this request type.")
        if request_obj.workflow_id != workflow.id:
            request_obj.workflow = workflow
            request_obj.save(update_fields=["workflow", "updated_at"])
        return WorkflowRuntimeService.start(workflow=workflow, target=request_obj, submitted_by=actor, request=request)

    @classmethod
    @transaction.atomic
    def fulfill(cls, *, request_obj, actor, request=None):
        from requests_app.models import BusinessRequest

        request_obj = BusinessRequest.objects.select_for_update().get(pk=request_obj.pk)
        if request_obj.status != "APPROVED":
            raise ValidationError("Only approved requests may be fulfilled.")
        if actor.company_id != request_obj.company_id or not CapabilityService.has(actor, Capabilities.FULFILL_REQUESTS):
            raise ValidationError("Request fulfillment permission is required.")
        request_obj.status = "FULFILLED"
        request_obj.fulfilled_at = timezone.now()
        request_obj.save(update_fields=["status", "fulfilled_at", "updated_at"])
        from records_management.finalizers import OfficialRecordFinalizer
        OfficialRecordFinalizer.maybe_issue(source=request_obj, actor=actor, workflow_instance=None, request=request)
        return request_obj


class BusinessRequestWorkflowAdapter:
    target_type = "REQUEST"

    @staticmethod
    def assert_submit_allowed(*, target, actor):
        if target.requester_id != actor.id or target.status not in {"DRAFT", "RETURNED"}:
            raise ValidationError("Request cannot be submitted.")

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
