from rest_framework.permissions import BasePermission

from core.roles import Roles


class CanManageWorkflows(BasePermission):

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
        )


class CanViewWorkflow(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):
        return (
            request.user
            and request.user.is_authenticated
        )