from rest_framework.permissions import BasePermission

from core.roles import Roles


class OrganizationPermission(BasePermission):
    """
    Base permission for organization-management resources.

    SUPERUSER:
        Platform-wide access.

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

        if not user or not user.is_authenticated:
            return False

        return user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )


class IsOrganizationAdmin(BasePermission):
    """
    Company administrator or platform superuser.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
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
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
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
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
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

        if not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        obj_company = getattr(obj, "company", None)

        if obj_company is None:
            return False

        return obj_company == user.company


class IsSameBranchObject(BasePermission):
    """
    Branch-level object restriction.

    SUPERUSER:
        Full access.

    ADMIN:
        Entire company.

    MANAGER:
        Their branch only.

    EMPLOYEE:
        Their branch only.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

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


class CanManageEmployees(BasePermission):
    """
    Controls employee-management operations.

    SUPERUSER:
        Platform-wide employee management.

    ADMIN:
        Company-wide employee management.

    MANAGER:
        Employee management within their branch.

    EMPLOYEE:
        Cannot manage employees.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        return user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == Roles.SUPERUSER:
            return True

        obj_company = getattr(obj, "company", None)

        if obj_company != user.company:
            return False

        if user.role == Roles.ADMIN:
            return True

        if user.role == Roles.MANAGER:
            return getattr(obj, "branch", None) == user.branch

        return False