from rest_framework.permissions import BasePermission
from .models import ProjectMembership


class IsProjectMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        return ProjectMembership.objects.filter(
            project=obj,
            user=request.user
        ).exists()


class IsProjectOwnerOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        return ProjectMembership.objects.filter(
            project=obj,
            user=request.user,
            role__in=["OWNER", "MANAGER"]
        ).exists()