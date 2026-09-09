from copy import deepcopy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class WorkflowDefinitionService:
    """Production lifecycle for workflow definitions.

    Published definitions are immutable. Editing a published definition creates a new draft
    version so existing WorkflowInstances remain explainable forever.
    """

    RECIPIENT_FIELDS = {
        "USER": "recipient_user",
        "ROLE": "recipient_role",
        "POSITION": "recipient_position",
        "REPORTER_MANAGER": None,
        "BRANCH_MANAGER": None,
        "DEPARTMENT_MANAGER": None,
        "TEAM_LEADER": None,
        "COMPANY_ADMIN": None,
    }

    @classmethod
    def validate_step(cls, *, company, step):
        from users.models import User
        from organizations.models import Position

        recipient_type = step.get("recipient_type")
        if recipient_type not in cls.RECIPIENT_FIELDS:
            raise ValidationError({"recipient_type": "Invalid recipient type."})

        required = cls.RECIPIENT_FIELDS[recipient_type]
        for field in ("recipient_user", "recipient_role", "recipient_position"):
            value = step.get(field)
            if field == required and not value:
                raise ValidationError({field: f"{field.replace('_', ' ').title()} is required."})
            if field != required and value not in (None, ""):
                raise ValidationError({field: f"{field.replace('_', ' ').title()} is not valid for {recipient_type}."})

        if recipient_type == "USER":
            if not User.objects.filter(pk=step["recipient_user"], company=company, is_active=True, is_deleted=False).exists():
                raise ValidationError({"recipient_user": "Recipient must be an active user in this company."})
        if recipient_type == "POSITION":
            if not Position.objects.filter(pk=step["recipient_position"], company=company, is_active=True).exists():
                raise ValidationError({"recipient_position": "Position must be active and belong to this company."})

        if step.get("approval_mode", "ANY") not in {"ANY", "ALL"}:
            raise ValidationError({"approval_mode": "Approval mode must be ANY or ALL."})

    @classmethod
    @transaction.atomic
    def create_draft(cls, *, company, actor, name, code, target_type, description="", steps=()):
        from workflows.models import WorkflowDefinition, WorkflowStepDefinition

        if not CapabilityService.has(actor, Capabilities.MANAGE_WORKFLOWS):
            raise ValidationError("Workflow management permission is required.")
        if actor.company_id != company.id:
            raise ValidationError("Cross-company workflow creation denied.")

        definition = WorkflowDefinition.objects.create(
            company=company,
            name=name,
            code=code,
            description=description,
            target_type=target_type,
            created_by=actor,
            is_active=False,
            lifecycle_status="DRAFT",
            version=1,
        )
        for order, step in enumerate(steps, 1):
            cls.validate_step(company=company, step=step)
            WorkflowStepDefinition.objects.create(workflow=definition, order=order, **step)
        return definition

    @classmethod
    @transaction.atomic
    def revise(cls, *, definition, actor, data):
        from workflows.models import WorkflowDefinition, WorkflowStepDefinition

        definition = WorkflowDefinition.objects.select_for_update().get(pk=definition.pk)
        if definition.company_id != actor.company_id:
            raise ValidationError("Cross-company workflow modification denied.")
        if not CapabilityService.has(actor, Capabilities.MANAGE_WORKFLOWS):
            raise ValidationError("Workflow management permission is required.")

        if getattr(definition, "lifecycle_status", "DRAFT") == "DRAFT" and not definition.instances.exists():
            target = definition
            target.name = data.get("name", target.name)
            target.description = data.get("description", target.description)
            target.save(update_fields=["name", "description", "updated_at"])
            if "steps" in data:
                target.steps.all().delete()
                for order, step in enumerate(data["steps"], 1):
                    cls.validate_step(company=target.company, step=step)
                    WorkflowStepDefinition.objects.create(workflow=target, order=order, **step)
            return target

        target = WorkflowDefinition.objects.create(
            company=definition.company,
            name=data.get("name", definition.name),
            code=definition.code,
            description=data.get("description", definition.description),
            target_type=definition.target_type,
            created_by=actor,
            is_active=False,
            lifecycle_status="DRAFT",
            version=definition.version + 1,
            supersedes=definition,
        )
        source_steps = data.get("steps")
        if source_steps is None:
            source_steps = [
                {
                    "name": s.name,
                    "recipient_type": s.recipient_type,
                    "recipient_user": s.recipient_user_id,
                    "recipient_role": s.recipient_role,
                    "recipient_position": s.recipient_position_id,
                    "approval_mode": s.approval_mode,
                    "can_reject": s.can_reject,
                    "can_return": s.can_return,
                    "notify_in_app": s.notify_in_app,
                    "notify_email": s.notify_email,
                    "is_required": s.is_required,
                }
                for s in definition.steps.order_by("order")
            ]
        for order, step in enumerate(deepcopy(source_steps), 1):
            cls.validate_step(company=target.company, step=step)
            WorkflowStepDefinition.objects.create(workflow=target, order=order, **step)
        return target

    @classmethod
    @transaction.atomic
    def publish(cls, *, definition, actor):
        from workflows.models import WorkflowDefinition

        definition = WorkflowDefinition.objects.select_for_update().get(pk=definition.pk)
        if definition.company_id != actor.company_id:
            raise ValidationError("Cross-company publish denied.")
        if not CapabilityService.has(actor, Capabilities.PUBLISH_WORKFLOWS):
            raise ValidationError("Workflow publishing permission is required.")
        if getattr(definition, "lifecycle_status", "DRAFT") != "DRAFT":
            raise ValidationError("Only a draft workflow can be published.")
        if not definition.steps.exists():
            raise ValidationError("At least one workflow step is required.")

        WorkflowDefinition.objects.filter(
            company=definition.company,
            code=definition.code,
            lifecycle_status="PUBLISHED",
        ).exclude(pk=definition.pk).update(is_active=False, lifecycle_status="ARCHIVED")
        definition.lifecycle_status = "PUBLISHED"
        definition.is_active = True
        definition.save(update_fields=["lifecycle_status", "is_active", "updated_at"])
        return definition
