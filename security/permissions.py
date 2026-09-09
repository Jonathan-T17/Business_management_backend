from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities
from core.capability_service import CapabilityService

class CanViewCompanySecurity(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.company_id and CapabilityService.has(request.user, Capabilities.VIEW_COMPANY_SECURITY))

class CanViewCompanyAudit(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.company_id and CapabilityService.has(request.user, Capabilities.VIEW_COMPANY_AUDIT))

class CanViewCompanySessions(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.company_id and CapabilityService.has(request.user, Capabilities.VIEW_COMPANY_SESSIONS))

class CanTerminateCompanySessions(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.company_id and CapabilityService.has(request.user, Capabilities.TERMINATE_COMPANY_SESSIONS))

class IsPlatformSecurity(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and CapabilityService.has(request.user, Capabilities.VIEW_PLATFORM_SECURITY))
