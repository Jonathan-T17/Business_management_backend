from core.roles import Roles
from projects.models import ProjectMembership


class ProjectAccess:

    @staticmethod
    def membership(user, project):
        """
        Return the ProjectMembership object if it exists, else None.
        """
        return ProjectMembership.objects.filter(
            project=project,
            user=user
        ).first()

    @staticmethod
    def is_member(user, project):
        """
        Check if the user is a member of the project.
        """
        return project.memberships.filter(user=user).exists()

    @staticmethod
    def is_manager(user, project):
        """
        Check if the user is an OWNER or MANAGER of the project.
        """
        return project.memberships.filter(
            user=user,
            role__in=["OWNER", "MANAGER"]
        ).exists()

    @staticmethod
    def is_owner(user, project):
        """
        Check if the user is the OWNER of the project.
        """
        return project.memberships.filter(
            user=user,
            role="OWNER"
        ).exists()

    @staticmethod
    def can_manage(user, project):
        """
        Determine if the user can manage the project.
        - SUPERUSER: always true
        - ADMIN: true if project belongs to their company
        - Otherwise: true if user is OWNER or MANAGER of the project
        """
        if user.role == Roles.SUPERUSER:
            return True

        if user.role == Roles.ADMIN:
            return project.company == user.company

        return ProjectAccess.is_manager(user, project)
