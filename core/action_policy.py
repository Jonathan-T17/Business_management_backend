from core.capabilities import Capabilities
from core.roles import Roles


def capabilities_for(user):
    from core.capability_service import CapabilityService

    return sorted(CapabilityService.all_for(user))


def actions_for(user, target=None):
    if not user or not user.is_authenticated:
        return []

    capabilities = set(capabilities_for(user))
    actions = set()

    if user.role == Roles.SUPERUSER:
        if target is not None and target.__class__.__name__ == "Company":
            actions.add("VIEW_SECURITY_HISTORY")
            actions.add("VIEW_SUPPORT_HISTORY")
            actions.add("CHANGE_SUBSCRIPTION")
            actions.add("REACTIVATE" if not target.is_active else "DEACTIVATE")
        elif target is not None and target.__class__.__name__ == "User":
            actions.add("VIEW_SECURITY_HISTORY")
            actions.add("TERMINATE_SESSIONS")
            actions.add("REQUIRE_PASSWORD_RESET")
            actions.add("ACTIVATE" if not target.is_active else "DEACTIVATE")
        else:
            actions.update({
                "VIEW_PLATFORM_HEALTH",
                "VIEW_PLATFORM_SECURITY",
                "VIEW_SUPPORT_INBOX",
            })
        return sorted(actions)

    if user.role == Roles.ADMIN:
        if Capabilities.MANAGE_EMPLOYEES in capabilities:
            actions.update({"INVITE_EMPLOYEE", "ACTIVATE_EMPLOYEE", "DEACTIVATE_EMPLOYEE"})
        if Capabilities.MANAGE_ORGANIZATION in capabilities:
            actions.update({"MANAGE_BRANCHES", "MANAGE_DEPARTMENTS", "MANAGE_TEAMS"})
        if Capabilities.MANAGE_COMPANY_PLANS in capabilities:
            actions.add("MANAGE_SUBSCRIPTION")
        actions.add("CONTACT_SMARTBIZ_SUPPORT")
        return sorted(actions)

    actions.add("CONTACT_SMARTBIZ_SUPPORT")
    return sorted(actions)