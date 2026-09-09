from rest_framework.permissions import BasePermission

from core.authorization import Authorization
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles


class RequiresCapability(BasePermission):
    """Reusable DRF permission for one required capability.

    Subclasses set ``required_capability``. Platform identities only pass for
    platform-only capabilities because CapabilityService enforces the boundary.
    """

    required_capability = None

    def has_permission(self, request, view):
        return bool(
            self.required_capability
            and Authorization.can_authenticate(request.user)
            and CapabilityService.has(request.user, self.required_capability)
        )


class IsSuperUserOrCompanyAdmin(BasePermission):
    """Backward-compatible name; intentionally tenant-admin only now.

    Platform control-plane users must use /api/platform/... endpoints.
    """

    def has_permission(self, request, view):
        return Authorization.can_authenticate(request.user) and Authorization.can_manage_company(
            request.user
        )


class IsCompanyManager(BasePermission):
    """Legacy tenant manager-or-admin check; never grants platform access."""

    def has_permission(self, request, view):
        user = request.user
        return Authorization.is_tenant_user(user) and user.role in (Roles.ADMIN, Roles.MANAGER)


class CanCreateTask(BasePermission):
    def has_permission(self, request, view):
        return Authorization.can_create_task(request.user)


class CanUpdateTask(BasePermission):
    def has_permission(self, request, view):
        return Authorization.can_update_task(request.user)


class CanCreateReport(BasePermission):
    def has_permission(self, request, view):
        return Authorization.can_create_report(request.user)


class CanManageUsers(RequiresCapability):
    required_capability = Capabilities.MANAGE_EMPLOYEES


class CanManageSubscription(RequiresCapability):
    required_capability = Capabilities.MANAGE_SUBSCRIPTION


class CanViewAnalytics(RequiresCapability):
    required_capability = Capabilities.VIEW_COMPANY_ANALYTICS


class CanManageWorkflows(RequiresCapability):
    required_capability = Capabilities.MANAGE_WORKFLOWS


class CanManageReportingSchedules(RequiresCapability):
    required_capability = Capabilities.MANAGE_REPORTING_SCHEDULES


class CanManageRequestTypes(RequiresCapability):
    required_capability = Capabilities.MANAGE_REQUEST_TYPES


class CanViewCompanySecurity(RequiresCapability):
    required_capability = Capabilities.VIEW_COMPANY_SECURITY


class IsPlatformAdmin(RequiresCapability):
    required_capability = Capabilities.PLATFORM_ADMIN
