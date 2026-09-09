from rest_framework.permissions import BasePermission

from core.roles import Roles


class IsCompanySetupAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated
            and user.role in (Roles.ADMIN, Roles.SUPERUSER)
            and (user.role == Roles.SUPERUSER or user.company_id is not None)
        )