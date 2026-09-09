from rest_framework.permissions import BasePermission

from core.roles import Roles


class CanManageFormTemplates(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ) -> bool:
        user = request.user

        if not user.is_authenticated:
            return False

        return user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )


class CanUseForms(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):

        user = request.user

        if not user.is_authenticated:
            return False

        return user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )