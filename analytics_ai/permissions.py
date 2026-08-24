from rest_framework.permissions import BasePermission


class IsAnalyticsAdmin(BasePermission):
    """
    Analytics are restricted to company-level administrators
    and the platform superuser.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return user.role in (
            "SUPERUSER",
            "ADMIN",
        )