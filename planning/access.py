from django.db.models import Q
from core.capability_service import CapabilityService
from core.capabilities import Capabilities


class PlanningAccessService:
    @classmethod
    def queryset(cls, *, user, queryset):
        if not getattr(user, "company_id", None):
            return queryset.none()
        queryset = queryset.filter(company_id=user.company_id)
        profile = getattr(user, "employee_profile", None)
        conditions = Q(created_by=user) | Q(owner=user) | Q(visibility="COMPANY")
        if user.branch_id:
            conditions |= Q(visibility="BRANCH", branch_id=user.branch_id)
        if profile and profile.department_id:
            conditions |= Q(visibility="DEPARTMENT", department_id=profile.department_id)
        if CapabilityService.has(user, getattr(Capabilities, "VIEW_COMPANY_PLANS", "VIEW_COMPANY_PLANS")):
            conditions |= Q(visibility="MANAGEMENT")
        return queryset.filter(conditions).distinct()

    @classmethod
    def can_manage(cls, *, user, plan):
        if plan.company_id != getattr(user, "company_id", None):
            return False
        return plan.owner_id == user.id or CapabilityService.has(user, Capabilities.MANAGE_COMPANY_PLANS)
