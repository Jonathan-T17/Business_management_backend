from rest_framework.permissions import BasePermission
from core.authorization import Authorization
from core.roles import Roles


class IsSuperUserOrCompanyAdmin(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_manage_company(request.user)



class IsCompanyManager(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (
                Roles.SUPERUSER,
                Roles.ADMIN,
                Roles.MANAGER,
            )
        )

# class IsCompanyManager(BasePermission):

#     def has_permission(self, request, view):
#         user = request.user

#         return (
#             user.is_authenticated
#             and user.role.value
#             if hasattr(user.role, "value")
#             else user.role
#         ) in ["SUPERUSER", "ADMIN", "MANAGER"]


class CanCreateTask(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_create_task(request.user)


class CanUpdateTask(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_update_task(request.user)


class CanCreateReport(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_create_report(request.user)


class CanManageUsers(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_manage_users(request.user)


class CanManageSubscription(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_manage_subscription(request.user)


class CanViewAnalytics(BasePermission):

    def has_permission(self, request, view):
        return Authorization.can_view_analytics(request.user)



# from rest_framework.permissions import BasePermission
# from core.roles import Roles
# from core.tenant import TenantService


# class RolePermission(BasePermission):
#     """
#     Base permission that checks if the user is authenticated
#     and has one of the allowed roles.
#     Also delegates object-level checks to TenantService.
#     """
#     allowed_roles = []

#     def has_permission(self, request, view):
#         return (
#             request.user.is_authenticated
#             and request.user.role in self.allowed_roles
#         )

#     def has_object_permission(self, request, view, obj):
#         user = request.user

#         # SUPERUSER always allowed
#         if user.role == Roles.SUPERUSER:
#             return True

#         # Company-level restriction
#         if user.role == Roles.ADMIN:
#             return getattr(obj, "company", None) == user.company

#         # Branch-level restriction
#         if user.role in [Roles.MANAGER, Roles.EMPLOYEE]:
#             return (
#                 getattr(obj, "company", None) == user.company
#                 and getattr(obj, "branch", None) == user.branch
#             )

#         # Self-only restriction
#         return obj == user


# # ✅ Atomic role checks
# class IsSuperUser(RolePermission):
#     allowed_roles = [Roles.SUPERUSER]


# class IsCompanyAdmin(RolePermission):
#     allowed_roles = [Roles.ADMIN]


# class IsManager(RolePermission):
#     allowed_roles = [Roles.MANAGER]


# class IsEmployee(RolePermission):
#     allowed_roles = [Roles.EMPLOYEE]


# # ✅ Combined role checks
# class IsSuperUserOrCompanyAdmin(RolePermission):
#     allowed_roles = [Roles.SUPERUSER, Roles.ADMIN]


# class IsManagerOrEmployee(RolePermission):
#     allowed_roles = [Roles.MANAGER, Roles.EMPLOYEE]


# class IsAuthenticatedUser(RolePermission):
#     allowed_roles = [
#         Roles.SUPERUSER,
#         Roles.ADMIN,
#         Roles.MANAGER,
#         Roles.EMPLOYEE,
#         Roles.INDIVIDUAL,
#     ]
