from rest_framework.permissions import BasePermission
from .models import ProjectMembership


class IsProjectMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return ProjectMembership.objects.filter(
            project=obj.project,
            user=request.user
        ).exists()


class IsProjectOwnerOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow read-only actions for members
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return ProjectMembership.objects.filter(
            project=obj.project,
            user=request.user,
            role__in=["OWNER", "MANAGER"]
        ).exists()