from rest_framework.permissions import BasePermission


class IsNotificationOwner(BasePermission):
    """
    Notifications can only be accessed by their recipient.
    """

    message = "You can only access your own notifications."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return obj.recipient_id == request.user.id