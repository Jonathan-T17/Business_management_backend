from rest_framework.permissions import BasePermission

from core.authorization import Authorization
from core.roles import Roles

from projects.models import ProjectMembership


class IsTaskMember(BasePermission):
    """
    Basic task/project access.

    A user must be authenticated and belong to the project.
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        return Authorization.can_create_task(user)

    def has_object_permission(self, request, view, obj):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        if obj.company_id != user.company_id:
            return False

        return ProjectMembership.objects.filter(
            project=obj.project,
            user=user,
        ).exists()


class CanManageTask(BasePermission):
    """
    Users allowed to create/update/delete tasks.

    Project OWNER and MANAGER can manage project tasks.
    Contributors may create/update tasks when allowed by
    the central authorization system.
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        return Authorization.can_create_task(user)

    def has_object_permission(self, request, view, obj):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.role == Roles.SUPERUSER:
            return True

        if obj.company_id != user.company_id:
            return False

        membership = ProjectMembership.objects.filter(
            project=obj.project,
            user=user,
        ).first()

        if not membership:
            return False

        if membership.role in (
            "OWNER",
            "MANAGER",
            "CONTRIBUTOR",
        ):
            return True

        return False


class IsTaskAssigneeOrManager(BasePermission):
    """
    Allows task assignees to work with their own tasks,
    while project owners/managers can manage all project tasks.
    """

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.role == Roles.SUPERUSER:
            return True

        if obj.company_id != user.company_id:
            return False

        membership = ProjectMembership.objects.filter(
            project=obj.project,
            user=user,
        ).first()

        if not membership:
            return False

        if membership.role in (
            "OWNER",
            "MANAGER",
        ):
            return True

        return obj.assignees.filter(
            id=user.id
        ).exists()