from rest_framework.permissions import BasePermission

from core.roles import Roles
from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class OrganizationPermission(BasePermission):
    """
    Base permission for organization-management resources.

    Platform identities cannot access tenant organization resources.

    ADMIN:
        Full organization management inside their company.

    MANAGER:
        Read organization information relevant to their branch.
        Management operations are controlled by endpoint-specific
        permissions.

    EMPLOYEE:
        Read organization information permitted to them.

    INDIVIDUAL:
        No organization-management access.
    """

    def has_permission(self, request, view):
        user = request.user

        if not CapabilityService.is_tenant_identity(user):
            return False

        return user.role in (
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )


class IsOrganizationAdmin(BasePermission):
    """
    Company administrator within a tenant.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            CapabilityService.is_tenant_identity(user)
            and user.role in (
                Roles.ADMIN,
            )
        )


class IsOrganizationManager(BasePermission):
    """
    Managers and above.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            CapabilityService.is_tenant_identity(user)
            and user.role in (
                Roles.ADMIN,
                Roles.MANAGER,
            )
        )


class CanViewOrganization(BasePermission):
    """
    Any authenticated organization user who has an
    organization-management role can view permitted data.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            CapabilityService.is_tenant_identity(user)
            and user.role in (
                Roles.ADMIN,
                Roles.MANAGER,
                Roles.EMPLOYEE,
            )
        )


class IsSameCompanyObject(BasePermission):
    """
    Object-level company isolation.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not CapabilityService.is_tenant_identity(user):
            return False

        obj_company = getattr(obj, "company", None)

        if obj_company is None:
            return False

        return obj_company == user.company


class IsSameBranchObject(BasePermission):
    """
    Branch-level object restriction.

    ADMIN:
        Entire company.

    MANAGER:
        Their branch only.

    EMPLOYEE:
        Their branch only.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not CapabilityService.is_tenant_identity(user):
            return False

        obj_company = getattr(obj, "company", None)

        if obj_company != user.company:
            return False

        if user.role == Roles.ADMIN:
            return True

        if user.role in (
            Roles.MANAGER,
            Roles.EMPLOYEE,
        ):
            obj_branch = getattr(obj, "branch", None)

            return obj_branch == user.branch

        return False


class CanViewCompensation(BasePermission):

    def has_permission(self, request, view):
        return (
            CapabilityService.is_tenant_identity(request.user)
            and CapabilityService.has(
                request.user,
                Capabilities.VIEW_COMPENSATION,
            )
        )


class CanManageCompensation(BasePermission):

    def has_permission(self, request, view):
        return (
            CapabilityService.is_tenant_identity(request.user)
            and CapabilityService.has(
                request.user,
                Capabilities.MANAGE_COMPENSATION,
            )
        )


class CanManageEmployees(BasePermission):
    """
    Controls employee-management operations.

    Requires MANAGE_EMPLOYEES. Existing company and branch object
    restrictions still apply; a role alone does not grant this authority.
    """

    def has_permission(self, request, view):
        user = request.user

        if not CapabilityService.is_tenant_identity(user):
            return False

        return CapabilityService.has(user, Capabilities.MANAGE_EMPLOYEES)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not self.has_permission(request, view):
            return False

        obj_company = getattr(obj, "company", None)

        if obj_company != user.company:
            return False

        if user.role == Roles.ADMIN:
            return True

        if user.role == Roles.MANAGER:
            return getattr(obj, "branch", None) == user.branch

        return False

class CanManageOrganization(BasePermission):
    def has_permission(self, request, view):
        return CapabilityService.is_tenant_identity(request.user) and CapabilityService.has(
            request.user, Capabilities.MANAGE_ORGANIZATION,
        )
