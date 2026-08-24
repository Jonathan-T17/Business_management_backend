from rest_framework.permissions import BasePermission

from core.roles import Roles


class IsCompanyMember(BasePermission):
    """
    Allows authenticated users who belong to an active company.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and getattr(user, "company_id", None) is not None
            and getattr(user.company, "is_active", False)
        )


class IsCompanyAdmin(BasePermission):
    """
    Company-level administration permission.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
                Roles.ADMIN,
            )
            and (
                user.role == Roles.SUPERUSER
                or getattr(user, "company_id", None) is not None
            )
        )


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == Roles.SUPERUSER
        )


class CanManageBranches(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
                Roles.ADMIN,
            )
            and getattr(user, "company_id", None) is not None
        )


class CanManageInvites(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
                Roles.ADMIN,
            )
            and getattr(user, "company_id", None) is not None
        )


class IsInviteRecipient(BasePermission):
    """
    Used when accepting an invitation.
    """

    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and request.user.email.lower() == obj.email.lower()
        )