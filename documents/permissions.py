from rest_framework.permissions import (
    BasePermission,
)

from core.roles import Roles


class CanManageDocuments(
    BasePermission
):

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
        )


class CanUseAttachments(
    BasePermission
):

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