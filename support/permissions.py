from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities
from core.capability_service import CapabilityService

class CanUseSupport(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u.is_authenticated and u.company_id and u.company and (u.company.is_active or getattr(view, "allow_inactive_company_support", False)))

class IsPlatformSupport(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and CapabilityService.has(request.user, Capabilities.PLATFORM_SUPPORT))

class CanManagePlatformSupport(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and CapabilityService.has(request.user, Capabilities.MANAGE_PLATFORM_SUPPORT))



# from rest_framework.permissions import BasePermission

# from core.authorization import Authorization
# from core.roles import Roles


# class CanUseSupport(BasePermission):
#     def has_permission(self, request, view):
#         user = request.user
#         return bool(
#             user.is_authenticated
#             and (
#                 Authorization.is_platform_superuser(user)
#                 or getattr(user, "company_id", None)
#                 and getattr(user.company, "is_active", False)
#             )
#         )


# class IsPlatformSupport(BasePermission):
#     def has_permission(self, request, view):
#         return Authorization.is_platform_superuser(request.user)


# class IsCompanySupportAdmin(BasePermission):
#     def has_permission(self, request, view):
#         user = request.user
#         return bool(user.is_authenticated and user.role == Roles.ADMIN and user.company_id)
