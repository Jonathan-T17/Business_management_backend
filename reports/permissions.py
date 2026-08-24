from rest_framework.permissions import BasePermission

from core.visibility import VisibilityService


class CanViewReport(BasePermission):
    """
    Object-level report visibility permission.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return VisibilityService.can_view_report(
            request.user,
            obj,
        )


can_view_report = VisibilityService.can_view_report