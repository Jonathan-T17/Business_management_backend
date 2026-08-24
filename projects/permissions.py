from rest_framework.permissions import BasePermission

from core.roles import Roles

from .models import ProjectMembership
from .project_roles import ProjectRoles


class IsProjectAuthenticated(BasePermission):
    """
    Basic authentication requirement.
    """

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
        )


class IsProjectMember(BasePermission):
    """
    User must be a member of the project.

    Company ADMIN/SUPERUSER can access projects
    belonging to their company without being explicitly
    added as project members.
    """

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        user = request.user

        project = getattr(
            obj,
            "project",
            obj,
        )

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        return ProjectMembership.objects.filter(
            project=project,
            user=user,
        ).exists()


class IsProjectManager(BasePermission):
    """
    Project OWNER or MANAGER.

    Company ADMIN/SUPERUSER also have management access
    inside their company.
    """

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        user = request.user

        project = getattr(
            obj,
            "project",
            obj,
        )

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        membership = ProjectMembership.objects.filter(
            project=project,
            user=user,
        ).first()

        if not membership:
            return False

        return membership.role in (
            ProjectRoles.OWNER.value,
            ProjectRoles.MANAGER.value,
        )


class IsProjectOwner(BasePermission):
    """
    Only project OWNER or company administrators/superuser.
    """

    def has_permission(self, request, view):

        return bool(
            request.user
            and request.user.is_authenticated
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):

        user = request.user

        project = getattr(
            obj,
            "project",
            obj,
        )

        if user.role == Roles.SUPERUSER:
            return True

        if (
            user.role == Roles.ADMIN
            and project.company_id == user.company_id
        ):
            return True

        return ProjectMembership.objects.filter(
            project=project,
            user=user,
            role=ProjectRoles.OWNER.value,
        ).exists()