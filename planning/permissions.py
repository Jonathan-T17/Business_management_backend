from rest_framework.permissions import BasePermission

from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class CanManagePlans(BasePermission):

    def has_permission(
        self,
        request,
        view,
    ):
        return (
            request.user.is_authenticated
            and CapabilityService.has(
                request.user,
                Capabilities.MANAGE_COMPANY_PLANS,
            )
        )