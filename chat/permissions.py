from rest_framework.permissions import BasePermission


class IsConversationMember(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        conversation = getattr(obj, "conversation", obj)
        return conversation.memberships.filter(user=request.user).exists()