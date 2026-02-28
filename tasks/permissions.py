from rest_framework.permissions import BasePermission
from projects.models import ProjectMembership


class IsProjectMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return ProjectMembership.objects.filter(
            project=obj.project,
            user=request.user
        ).exists()