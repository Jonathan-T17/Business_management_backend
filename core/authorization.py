from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles


class Authorization:
    """Compatibility authorization facade.

    New code should prefer explicit CapabilityService + VisibilityService
    checks. These methods remain so existing apps can migrate incrementally
    without preserving the old SUPERUSER/ADMIN bypass model.
    """

    @staticmethod
    def is_platform_superuser(user):
        return CapabilityService.is_platform_identity(user)

    @staticmethod
    def is_tenant_user(user):
        return CapabilityService.is_tenant_identity(user)

    @staticmethod
    def can_authenticate(user):
        if not user or not getattr(user, "is_authenticated", False):
            return False

        if not getattr(user, "is_active", False) or getattr(user, "is_deleted", False):
            return False

        # Platform identities are valid without a tenant company.
        if Authorization.is_platform_superuser(user):
            return True

        company = getattr(user, "company", None)
        return bool(company and getattr(company, "is_active", False))

    @staticmethod
    def same_tenant(user, obj):
        if not Authorization.is_tenant_user(user):
            return False
        return getattr(obj, "company_id", None) == user.company_id

    @staticmethod
    def is_superuser(user):
        return Authorization.is_platform_superuser(user)

    @staticmethod
    def is_admin(user):
        return Authorization.is_tenant_user(user) and user.role == Roles.ADMIN

    @staticmethod
    def is_manager(user):
        return Authorization.is_tenant_user(user) and user.role == Roles.MANAGER

    @staticmethod
    def is_employee(user):
        return Authorization.is_tenant_user(user) and user.role == Roles.EMPLOYEE

    @staticmethod
    def can_manage_company(user):
        return CapabilityService.has(user, Capabilities.MANAGE_ORGANIZATION)

    @staticmethod
    def can_manage_branch(user):
        return CapabilityService.has(user, Capabilities.MANAGE_ORGANIZATION)

    @staticmethod
    def can_create_project(user):
        return CapabilityService.has(user, Capabilities.MANAGE_PROJECTS)

    @staticmethod
    def can_update_project(user):
        return CapabilityService.has(user, Capabilities.MANAGE_PROJECTS)

    @staticmethod
    def can_delete_project(user):
        return CapabilityService.has(user, Capabilities.MANAGE_PROJECTS)

    @staticmethod
    def can_create_task(user):
        return CapabilityService.has(user, Capabilities.MANAGE_TASKS)

    @staticmethod
    def can_update_task(user):
        return CapabilityService.has(user, Capabilities.MANAGE_TASKS)

    @staticmethod
    def can_complete_task(user):
        # Final task authorization must additionally check assignment/project role.
        return Authorization.is_tenant_user(user)

    @staticmethod
    def can_create_report(user):
        return Authorization.is_tenant_user(user) and user.role != Roles.INDIVIDUAL

    @staticmethod
    def can_create_comment(user):
        # Final authorization must additionally check source visibility.
        return Authorization.is_tenant_user(user)

    @staticmethod
    def can_manage_users(user):
        return CapabilityService.has(user, Capabilities.MANAGE_EMPLOYEES)

    @staticmethod
    def can_invite_member(user):
        return CapabilityService.has(user, Capabilities.MANAGE_EMPLOYEES)

    @staticmethod
    def can_remove_member(user):
        return CapabilityService.has(user, Capabilities.MANAGE_EMPLOYEES)

    @staticmethod
    def can_change_owner(user):
        return CapabilityService.has(user, Capabilities.MANAGE_PROJECTS)

    @staticmethod
    def can_manage_subscription(user):
        return CapabilityService.has(user, Capabilities.MANAGE_SUBSCRIPTION)

    @staticmethod
    def can_view_analytics(user):
        return CapabilityService.has(user, Capabilities.VIEW_COMPANY_ANALYTICS)

    @staticmethod
    def can_manage_company_settings(user):
        return CapabilityService.has(user, Capabilities.MANAGE_ORGANIZATION)
