from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from security.services import create_audit_log
from .access import PlanningAccessService


class PlanningService:
    TRANSITIONS = {
        "DRAFT": {"ACTIVE", "CANCELLED", "ARCHIVED"},
        "ACTIVE": {"COMPLETED", "CANCELLED", "ARCHIVED"},
        "COMPLETED": {"ARCHIVED"},
        "CANCELLED": {"ARCHIVED"},
        "ARCHIVED": set(),
    }

    @classmethod
    @transaction.atomic
    def transition(cls, *, plan, user, to_status, request=None):
        plan = type(plan).objects.select_for_update().get(pk=plan.pk)
        if not PlanningAccessService.can_manage(user=user, plan=plan):
            raise PermissionDenied("Plan management denied.")
        if to_status not in cls.TRANSITIONS.get(plan.status, set()):
            raise ValidationError(f"Cannot transition plan from {plan.status} to {to_status}.")
        plan.status = to_status
        plan.save(update_fields=["status", "updated_at"])
        create_audit_log(user=user, company=plan.company, request=request, action="UPDATE", description=f"Plan transitioned to {to_status}.", obj=plan)
        return plan

    @classmethod
    @transaction.atomic
    def update_item(cls, *, item, user, values, request=None):
        item = type(item).objects.select_for_update().select_related("plan").get(pk=item.pk)
        if not PlanningAccessService.can_manage(user=user, plan=item.plan) and item.owner_id != user.id:
            raise PermissionDenied("Plan item management denied.")
        for field in ("title", "description", "owner", "target_value", "actual_value", "unit", "due_date", "status", "order"):
            if field in values:
                setattr(item, field, values[field])
        if getattr(item, "project_id", None) and item.project.company_id != item.plan.company_id:
            raise ValidationError("Project belongs to another company.")
        if getattr(item, "task_id", None) and item.task.company_id != item.plan.company_id:
            raise ValidationError("Task belongs to another company.")
        item.save()
        return item
