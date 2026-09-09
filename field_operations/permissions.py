from rest_framework.permissions import BasePermission

from core.roles import Roles


class CanUseFieldOperations(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):
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


class CanManageFieldOperations(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        return (
            user.is_authenticated
            and user.role in (
                Roles.SUPERUSER,
                Roles.ADMIN,
                Roles.MANAGER,
            )
        )