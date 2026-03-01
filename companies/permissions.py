from rest_framework.permissions import BasePermission


class IsCompanyAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == "ADMIN"
        )


class IsCompanyMember(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.company is not None