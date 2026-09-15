from rest_framework.permissions import BasePermission

from core.roles import Roles
from core.capability_service import CapabilityService


class CanManageWorkflows(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):
        user = request.user

        if not CapabilityService.is_tenant_identity(user):
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