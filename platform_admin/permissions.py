from rest_framework.permissions import BasePermission

from core.roles import Roles


class IsPlatformSuperUser(BasePermission):
    """
    Platform-level administration only.
    """

    message = (
        "Platform administrator access is required."
    )

    def has_permission(self, request, view):
        user = request.user

        if (
            not user
            or not user.is_authenticated
        ):
            return False

        return (
            bool(user.is_superuser)
            or user.role == Roles.SUPERUSER
        )