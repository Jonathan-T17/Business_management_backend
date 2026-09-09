from rest_framework.permissions import BasePermission
from core.capability_service import CapabilityService
from core.capabilities import Capabilities

class IsCompanySetupAdmin(BasePermission):
    """
    Tenant setup is tenant-only. Platform identities must use platform control
    routes or an explicit Support Mode grant, never a SUPERUSER bypass.
    """
    message = "Company setup authority is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "company_id", None)
            and CapabilityService.has(user, Capabilities.MANAGE_COMPANY_SETUP)
        )
