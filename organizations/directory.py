"""Directory visibility and aggregate counts share one permission boundary."""
from django.db.models import Q

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.position_scope import PositionScope
from core.roles import Roles


def directory_scope(user):
    if not CapabilityService.is_tenant_identity(user):
        return "NONE", set()
    if any(CapabilityService.has_company(user, cap) for cap in (
        Capabilities.VIEW_ALL_EMPLOYEES, Capabilities.MANAGE_EMPLOYEES,
    )):
        return "COMPANY", set()
    branches = PositionScope.branches_for(user, Capabilities.VIEW_ALL_EMPLOYEES)
    # Preserve existing manager directory access, without treating a missing
    # branch as permission to read all unassigned profiles.
    if user.role == Roles.MANAGER and user.branch_id:
        branches.add(user.branch_id)
    return ("BRANCHES", branches) if branches else ("PERSONAL", set())


def directory_queryset(user, queryset):
    scope, branches = directory_scope(user)
    if scope == "NONE":
        return queryset.none()
    queryset = queryset.filter(company_id=user.company_id, user__company_id=user.company_id, user__is_deleted=False)
    if scope == "COMPANY":
        return queryset
    if scope == "BRANCHES":
        return queryset.filter(Q(branch_id__in=branches) | Q(user_id=user.pk))
    return queryset.filter(user_id=user.pk)
