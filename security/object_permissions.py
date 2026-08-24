from rest_framework.permissions import BasePermission

from core.roles import Roles


class TenantObjectPermission(BasePermission):
    """
    Generic object-level permission
    shared by every app.
    """

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        user = request.user

        if not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        if hasattr(obj, "company"):

            if obj.company != user.company:
                return False

        if (
            user.role == Roles.ADMIN
        ):
            return True

        if hasattr(obj, "branch"):

            if user.role == Roles.MANAGER:
                return obj.branch == user.branch

            if user.role == Roles.EMPLOYEE:
                return (
                    obj.branch == user.branch
                )

        if hasattr(obj, "created_by"):

            return obj.created_by == user

        return False
    



from rest_framework.exceptions import PermissionDenied
from core.roles import Roles


class CompanyObjectPermission:
    """
    Enforces company/branch object-level restrictions.
    Managers can act on employees in their branch.
    """

    @staticmethod
    def validate(user, obj):
        # Superuser always allowed
        if user.role == Roles.SUPERUSER:
            return

        # Company restriction
        if getattr(obj, "company", None) != getattr(user, "company", None):
            raise PermissionDenied("Company access denied.")

        # Branch restriction
        if hasattr(obj, "branch"):
            # Managers can act on employees in their branch
            if user.role == Roles.MANAGER:
                if getattr(obj, "branch", None) != getattr(user, "branch", None):
                    raise PermissionDenied("Branch access denied.")
                # If obj is a user, allow if that user is an employee in same branch
                if hasattr(obj, "role") and obj.role == Roles.EMPLOYEE:
                    return

            # Employees can only act on themselves
            if user.role == Roles.EMPLOYEE:
                if getattr(obj, "branch", None) != getattr(user, "branch", None):
                    raise PermissionDenied("Branch access denied.")
                if obj != user:
                    raise PermissionDenied("Employees can only manage themselves.")
