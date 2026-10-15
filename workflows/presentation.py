"""Read-only approval actions, evaluated using the runtime's access rules."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from core.capability_service import CapabilityService
from core.visibility import VisibilityService
from workflows.runtime_service import WorkflowTargetAdapterRegistry
from workflows.services import WorkflowService


def review_context(instance, actor):
    steps = sorted(instance.steps.all(), key=lambda step: step.order)
    step = next((step for step in steps if step.status == "PENDING"), None)
    result = {"current_step": {"id": str(step.pk), "name": step.name, "order": step.order} if step else None,
              "allowed_actions": [], "acting_for": None, "delegated": False}
    if not actor or not CapabilityService.is_tenant_identity(actor) or actor.company_id != instance.company_id:
        return result
    if instance.status != "IN_PROGRESS" or not step:
        return result
    try:
        target = instance.content_object
        if target is None:
            return result
        if not VisibilityService.can_view_generic_object(user=actor, obj=target):
            WorkflowTargetAdapterRegistry.for_target(target).assert_participant_review_allowed(
                target=target, actor=actor, workflow_instance=instance)
        recipient = WorkflowService._recipient_for_user(step, actor, permission=WorkflowService._delegation_permission(instance))
    except (ValidationError, DjangoValidationError):
        return result
    result["allowed_actions"] = ["APPROVE"]
    if step.can_return:
        result["allowed_actions"].append("RETURN")
    if step.can_reject:
        result["allowed_actions"].append("REJECT")
    result["delegated"] = recipient.user_id != actor.pk
    if result["delegated"]:
        result["acting_for"] = {"id": str(recipient.user_id), "full_name": recipient.user.full_name}
    return result
