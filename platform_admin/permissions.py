from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities
from core.capability_service import CapabilityService

class RequiresPlatformCapability(BasePermission):
    capability = None
    def has_permission(self, request, view):
        cap = getattr(view, "required_platform_capability", self.capability)
        return bool(cap and request.user.is_authenticated and CapabilityService.has(request.user, cap))

class CanManagePlatformCompanies(RequiresPlatformCapability): capability = Capabilities.MANAGE_PLATFORM_COMPANIES
class CanManagePlatformUsers(RequiresPlatformCapability): capability = Capabilities.MANAGE_PLATFORM_USERS
class CanManagePlatformSubscriptions(RequiresPlatformCapability): capability = Capabilities.MANAGE_PLATFORM_SUBSCRIPTIONS
class CanViewPlatformSecurity(RequiresPlatformCapability): capability = Capabilities.VIEW_PLATFORM_SECURITY
class CanViewPlatformHealth(RequiresPlatformCapability): capability = Capabilities.VIEW_PLATFORM_HEALTH
class CanUsePlatformSupport(RequiresPlatformCapability): capability = Capabilities.PLATFORM_SUPPORT
