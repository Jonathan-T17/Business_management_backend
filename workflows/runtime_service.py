from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.visibility import VisibilityService


class WorkflowTargetAdapterRegistry:
    _registry = {}

    @classmethod
    def register(cls, model, adapter):
        cls._registry[model] = adapter

    @classmethod
    def for_target(cls, target):
        for model, adapter in cls._registry.items():
            if isinstance(target, model):
                return adapter
        raise ValidationError("This object type is not workflow-enabled.")


class WorkflowRuntimeService:
    """Concurrency-safe runtime workflow engine.

    It deliberately does not write arbitrary target.status fields. A source-specific adapter
    owns lifecycle transitions and official-record finalization.
    """

    @classmethod
    @transaction.atomic
    def start(cls, *, workflow, target, submitted_by, request=None):
        from workflows.models import WorkflowInstance, WorkflowStepInstance, WorkflowStepRecipient, WorkflowActionLog
        from workflows.services import WorkflowService as LegacyWorkflowService

        if workflow.company_id != submitted_by.company_id or getattr(target, "company_id", None) != submitted_by.company_id:
            raise ValidationError("Cross-company workflow submission denied.")
        if not workflow.is_active or getattr(workflow, "lifecycle_status", "PUBLISHED") != "PUBLISHED":
            raise ValidationError("Only a published workflow may be started.")

        adapter = WorkflowTargetAdapterRegistry.for_target(target)
        if workflow.target_type != adapter.target_type:
            raise ValidationError("Workflow target type does not match this object.")
        adapter.assert_submit_allowed(target=target, actor=submitted_by)

        ct = ContentType.objects.get_for_model(target, for_concrete_model=False)
        existing = WorkflowInstance.objects.select_for_update().filter(
            company=workflow.company,
            content_type=ct,
            object_id=str(target.pk),
            status="IN_PROGRESS",
        ).first()
        if existing:
            raise ValidationError("This item already has an active workflow.")

        instance = WorkflowInstance.objects.create(
            company=workflow.company,
            workflow=workflow,
            content_type=ct,
            object_id=str(target.pk),
            submitted_by=submitted_by,
            status="IN_PROGRESS",
            workflow_version=getattr(workflow, "version", 1),
        )

        runtimes = []
        for definition in workflow.steps.order_by("order"):
            recipients = list(LegacyWorkflowService.resolve_recipients(
                step=definition, company=workflow.company, target=target, submitted_by=submitted_by,
            ))
            runtime = WorkflowStepInstance.objects.create(
                workflow_instance=instance,
                definition_step=definition,
                order=definition.order,
                name=definition.name,
                approval_mode=definition.approval_mode,
                can_reject=definition.can_reject,
                can_return=definition.can_return,
                status="WAITING",
                routing_snapshot={
                    "recipient_type": definition.recipient_type,
                    "recipient_role": definition.recipient_role,
                    "recipient_user_id": str(definition.recipient_user_id) if definition.recipient_user_id else None,
                    "recipient_position_id": str(definition.recipient_position_id) if definition.recipient_position_id else None,
                    "notify_in_app": definition.notify_in_app,
                    "notify_email": definition.notify_email,
                    "is_required": definition.is_required,
                },
            )
            if not recipients:
                if definition.is_required:
                    raise ValidationError(f"No eligible recipient could be resolved for '{definition.name}'.")
                runtime.status = "SKIPPED"
                runtime.completed_at = timezone.now()
                runtime.save(update_fields=["status", "completed_at"])
            else:
                for user in recipients:
                    WorkflowStepRecipient.objects.create(step=runtime, user=user)
            runtimes.append(runtime)

        WorkflowActionLog.objects.create(workflow_instance=instance, actor=submitted_by, action="SUBMITTED")
        adapter.on_submitted(target=target, actor=submitted_by, workflow_instance=instance, request=request)
        cls._activate_next(instance=instance, target=target, actor=submitted_by, request=request)
        return instance

    @classmethod
    def _activate_next(cls, *, instance, target, actor, request=None):
        from workflows.services import WorkflowService as LegacyWorkflowService

        next_step = instance.steps.filter(status="WAITING").order_by("order").first()
        if next_step:
            next_step.status = "PENDING"
            next_step.started_at = timezone.now()
            next_step.save(update_fields=["status", "started_at"])
            LegacyWorkflowService._notify_step(next_step, target)
            return
        cls._approve_instance(instance=instance, actor=actor, request=request)

    @classmethod
    @transaction.atomic
    def approve(cls, *, instance, actor, note="", request=None):
        from workflows.models import WorkflowInstance, WorkflowActionLog
        from workflows.services import WorkflowService as LegacyWorkflowService

        instance = WorkflowInstance.objects.select_for_update().select_related("content_type").get(pk=instance.pk)
        if instance.status != "IN_PROGRESS":
            raise ValidationError("This workflow is no longer active.")
        target = instance.content_object
        if not VisibilityService.can_view_generic_object(user=actor, obj=target):
            # workflow participation is additionally checked by _recipient_for_user below;
            # this prevents participation from widening unrelated sensitive source data.
            adapter = WorkflowTargetAdapterRegistry.for_target(target)
            adapter.assert_participant_review_allowed(target=target, actor=actor, workflow_instance=instance)

        step = instance.steps.select_for_update().filter(status="PENDING").order_by("order").first()
        if not step:
            raise ValidationError("There is no pending workflow step.")
        recipient = LegacyWorkflowService._recipient_for_user(
            step, actor, permission=LegacyWorkflowService._delegation_permission(instance)
        )
        if recipient.status != "PENDING":
            raise ValidationError("This approval assignment has already been acted on.")

        recipient.status = "APPROVED"
        recipient.acted_at = timezone.now()
        recipient.note = note
        recipient.save(update_fields=["status", "acted_at", "note"])
        WorkflowActionLog.objects.create(
            workflow_instance=instance,
            step=step,
            actor=actor,
            action="APPROVED",
            note=note,
            metadata={"delegated": recipient.user_id != actor.id, "acting_for_user_id": str(recipient.user_id) if recipient.user_id != actor.id else None},
        )

        complete = step.approval_mode == "ANY" or not step.recipients.exclude(status__in=["APPROVED", "SKIPPED"]).exists()
        if step.approval_mode == "ANY":
            step.recipients.filter(status="PENDING").exclude(pk=recipient.pk).update(status="SKIPPED")
        if not complete:
            return instance

        step.status = "APPROVED"
        step.completed_at = timezone.now()
        step.save(update_fields=["status", "completed_at"])
        cls._activate_next(instance=instance, target=target, actor=actor, request=request)
        instance.refresh_from_db()
        if not instance.steps.filter(status__in=["WAITING", "PENDING"]).exists() and instance.status == "IN_PROGRESS":
            cls._approve_instance(instance=instance, actor=actor, request=request)
        return instance

    @classmethod
    def _approve_instance(cls, *, instance, actor, request=None):
        if instance.status != "IN_PROGRESS":
            return instance
        instance.status = "APPROVED"
        instance.completed_at = timezone.now()
        instance.save(update_fields=["status", "completed_at"])
        adapter = WorkflowTargetAdapterRegistry.for_target(instance.content_object)
        adapter.on_approved(target=instance.content_object, actor=actor, workflow_instance=instance, request=request)
        return instance

    @classmethod
    @transaction.atomic
    def reject(cls, *, instance, actor, note="", request=None):
        return cls._end_step(instance=instance, actor=actor, note=note, outcome="REJECTED", request=request)

    @classmethod
    @transaction.atomic
    def return_for_changes(cls, *, instance, actor, note="", request=None):
        return cls._end_step(instance=instance, actor=actor, note=note, outcome="RETURNED", request=request)

    @classmethod
    def _end_step(cls, *, instance, actor, note, outcome, request=None):
        from workflows.models import WorkflowInstance, WorkflowActionLog
        from workflows.services import WorkflowService
        instance = WorkflowInstance.objects.select_for_update().get(pk=instance.pk)
        if instance.status != "IN_PROGRESS" or not note.strip():
            raise ValidationError("An active workflow and a reason are required.")
        if actor.company_id != instance.company_id:
            raise ValidationError("Workflow is not available to this company.")
        target = instance.content_object
        adapter = WorkflowTargetAdapterRegistry.for_target(target)
        if not VisibilityService.can_view_generic_object(user=actor, obj=target):
            adapter.assert_participant_review_allowed(target=target, actor=actor, workflow_instance=instance)
        step = instance.steps.select_for_update().filter(status="PENDING").order_by("order").first()
        if not step or not getattr(step, "can_reject" if outcome == "REJECTED" else "can_return"):
            raise ValidationError("This step does not permit that action.")
        recipient = WorkflowService._recipient_for_user(step, actor, permission=WorkflowService._delegation_permission(instance))
        if recipient.status != "PENDING":
            raise ValidationError("This assignment has already been acted on.")
        recipient.status, recipient.note, recipient.acted_at = outcome, note, timezone.now()
        recipient.save(update_fields=["status", "note", "acted_at"])
        step.recipients.filter(status="PENDING").update(status="SKIPPED")
        step.status, step.completed_at = outcome, timezone.now()
        step.save(update_fields=["status", "completed_at"])
        instance.steps.filter(status="WAITING").update(status="SKIPPED", completed_at=timezone.now())
        instance.status, instance.completed_at = outcome, timezone.now()
        instance.save(update_fields=["status", "completed_at"])
        WorkflowActionLog.objects.create(workflow_instance=instance, step=step, actor=actor, action=outcome, note=note)
        callback = adapter.on_rejected if outcome == "REJECTED" else adapter.on_returned
        callback(target=target, actor=actor, workflow_instance=instance, request=request)
        return instance
