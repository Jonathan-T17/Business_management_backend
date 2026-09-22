from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class IsAnalyticsAdmin(BasePermission):
    """Tenant analytics requires explicit company analytics authority."""
    def has_permission(self, request, view):
        return CapabilityService.is_tenant_identity(request.user) and CapabilityService.has_company(
            request.user, Capabilities.VIEW_COMPANY_ANALYTICS,
        )
