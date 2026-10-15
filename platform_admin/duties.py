from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService


class PlatformDutyPermission(BasePermission):
    """Read and containment authority are distinct; unspecified routes remain owner-only."""
    def has_permission(self, request, view):
        if CapabilityService.has(request.user, C.PLATFORM_ADMIN):
            return True
        read = {"PlatformActiveSessionViewSet": C.VIEW_PLATFORM_SECURITY,
                "PlatformLoginHistoryViewSet": C.VIEW_PLATFORM_SECURITY,
                "PlatformFailedLoginViewSet": C.VIEW_PLATFORM_SECURITY,
                "PlatformAuditLogViewSet": C.VIEW_PLATFORM_AUDIT,
                "PlatformHealthView": C.VIEW_PLATFORM_HEALTH,
                "PlatformPlanViewSet": C.MANAGE_PLATFORM_SUBSCRIPTIONS,
                "PlatformSubscriptionViewSet": C.MANAGE_PLATFORM_SUBSCRIPTIONS}
        name = view.__class__.__name__
        capability = read.get(name) if request.method in ("GET", "HEAD", "OPTIONS") else None
        if name in ("PlatformActiveSessionViewSet", "PlatformFailedLoginViewSet") and getattr(view, "action", "") in ("terminate", "unlock"):
            capability = C.MANAGE_PLATFORM_SECURITY
        if name == "PlatformSubscriptionViewSet" and getattr(view, "action", "") == "change_plan":
            capability = C.MANAGE_PLATFORM_SUBSCRIPTIONS
        return bool(capability and CapabilityService.has(request.user, capability))
