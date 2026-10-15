from rest_framework.permissions import BasePermission
from core.roles import Roles


class IsSuperUserOrPlatformAdmin(BasePermission):
    """
    Allows access only to verified platform operators.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        from core.capability_service import CapabilityService
        from core.capabilities import Capabilities
        return CapabilityService.has(user, Capabilities.PLATFORM_ADMIN)


class RolePermission:
    """
    Centralized role checks based on Roles constants.
    """

    @staticmethod
    def is_superuser(user):
        from core.capability_service import CapabilityService
        from core.capabilities import Capabilities
        return CapabilityService.has(user, Capabilities.PLATFORM_ADMIN)

    @staticmethod
    def is_admin(user):
        from core.capability_service import CapabilityService
        return CapabilityService.is_tenant_identity(user) and user.role == Roles.ADMIN

    @staticmethod
    def is_manager(user):
        return user.role == Roles.MANAGER

    @staticmethod
    def is_employee(user):
        return user.role == Roles.EMPLOYEE

    @staticmethod
    def is_individual(user):
        return user.role == Roles.INDIVIDUAL


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and RolePermission.is_superuser(request.user)
        )


class IsCompanyAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and RolePermission.is_admin(request.user)
        )


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and RolePermission.is_manager(request.user)
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and RolePermission.is_employee(request.user)
        )


class IsCompanyMember(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role != Roles.INDIVIDUAL
        )



from rest_framework.permissions import BasePermission

class IsSelf(BasePermission):
    """
    Allows access only if the user is acting on their own resource.
    For example, updating their own profile.
    """

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and obj.id == request.user.id
