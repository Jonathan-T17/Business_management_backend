from rest_framework.permissions import BasePermission


class IsCommentParticipant(BasePermission):
    """
    Allows access only when the authenticated user is authorized
    to interact with the comment's project.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "company_id", None) is not None
        )

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Tenant isolation
        if obj.company_id != user.company_id:
            return False

        project = obj.project

        # Superuser
        if getattr(user, "role", None) == "SUPERUSER":
            return True

        # Company admin
        if getattr(user, "role", None) == "ADMIN":
            return True

        # Project membership
        return project.memberships.filter(
            user=user
        ).exists()