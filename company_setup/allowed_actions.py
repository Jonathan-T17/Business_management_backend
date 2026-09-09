from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from .readiness import SetupReadinessService

class SetupAllowedActions:
    @classmethod
    def for_user(cls, user):
        if not getattr(user, "company_id", None):
            return []
        actions = []
        if CapabilityService.has(user, Capabilities.MANAGE_COMPANY_SETUP):
            actions += [
                "EDIT_COMPANY_PROFILE",
                "APPLY_BUSINESS_TEMPLATE",
                "MANAGE_ORGANIZATION_SETUP",
                "INVITE_EMPLOYEES",
                "MANAGE_ROLE_PRESETS",
                "MANAGE_REQUEST_TYPES",
                "MANAGE_FIELD_TEMPLATES",
                "MANAGE_APPROVAL_ROUTES",
                "MANAGE_REPORTING_PROCESSES",
                "MANAGE_DOCUMENT_CATEGORIES",
                "MANAGE_NOTIFICATION_POLICIES",
                "MANAGE_OFFICIAL_RECORD_POLICIES",
            ]
            if SetupReadinessService.evaluate(user.company)["ready"]:
                actions.append("FINISH_ONBOARDING")
        return actions
