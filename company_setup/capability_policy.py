from rest_framework.exceptions import PermissionDenied, ValidationError
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from .setup_contract import SENSITIVE_CAPABILITIES

class SetupCapabilityPolicy:
    @classmethod
    def validate_preset(cls, *, actor, capabilities):
        requested = set(capabilities or [])
        invalid = requested - set(Capabilities.values())
        if invalid:
            raise ValidationError(
                {"capabilities": f"Unknown capabilities: {', '.join(sorted(invalid))}."}
            )

        platform_only = requested & set(Capabilities.PLATFORM_ONLY)
        if platform_only:
            raise PermissionDenied("Platform-only capabilities cannot be assigned by a company.")

        # Configuration authority must not bootstrap content authority that the
        # actor does not themselves possess.
        unowned_sensitive = {
            code for code in requested & SENSITIVE_CAPABILITIES
            if not CapabilityService.has(actor, code)
        }
        if unowned_sensitive:
            raise PermissionDenied(
                "You cannot grant sensitive capabilities you do not possess."
            )
        return sorted(requested)

    @classmethod
    def warnings(cls, capabilities):
        requested = set(capabilities or [])
        return [
            {
                "code": code,
                "severity": "HIGH",
                "message": f"{code.replace('_', ' ').title()} grants access to sensitive data or security operations.",
            }
            for code in sorted(requested & SENSITIVE_CAPABILITIES)
        ]
