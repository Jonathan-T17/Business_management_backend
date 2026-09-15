from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class CanManageDocuments(BasePermission):
    def has_permission(self, request, view):
        return CapabilityService.is_tenant_identity(request.user) and CapabilityService.has(
            request.user, Capabilities.MANAGE_DOCUMENTS,
        )


class CanUseAttachments(BasePermission):
    def has_permission(self, request, view):
        # Object visibility and mutation rules remain enforced by the view/service.
        return CapabilityService.is_tenant_identity(request.user)
