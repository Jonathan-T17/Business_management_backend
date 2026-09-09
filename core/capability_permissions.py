from rest_framework.permissions import BasePermission

from core.capability_service import CapabilityService


class RequiresCapability(BasePermission):

    required_capability = None

    def has_permission(self, request, view):
        capability = getattr(
            view,
            "required_capability",
            self.required_capability,
        )

        if not capability:
            return False

        return CapabilityService.has(request.user, capability)