from django.db.models import Q
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from .models import Project, ProjectMembership
from .project_roles import ProjectRoles

class ProjectAccess:
    """Single source of truth for tenant project visibility/action authority."""

    @staticmethod
    def membership(user, project):
        if not getattr(user, 'company_id', None) or project.company_id != user.company_id:
            return None
        return ProjectMembership.objects.filter(project=project, user=user).first()

    @classmethod
    def visible_queryset(cls, user, queryset=None, *, include_archived=False):
        queryset = queryset or Project.objects.all()
        if not getattr(user, 'company_id', None):
            return queryset.none()
        queryset = queryset.filter(company_id=user.company_id)
        if not include_archived:
            queryset = queryset.filter(is_active=True)
        # Project content is membership-scoped. Company configuration authority does not
        # silently create content visibility.
        return queryset.filter(memberships__user=user).distinct()

    @classmethod
    def can_view(cls, user, project):
        return cls.membership(user, project) is not None

    @classmethod
    def can_create(cls, user):
        return bool(getattr(user, 'company_id', None) and CapabilityService.has(user, Capabilities.MANAGE_PROJECTS))

    @classmethod
    def can_manage(cls, user, project):
        membership = cls.membership(user, project)
        return bool(
            membership
            and membership.role in (ProjectRoles.OWNER.value, ProjectRoles.MANAGER.value)
            and CapabilityService.has(user, Capabilities.MANAGE_PROJECTS)
        )

    @classmethod
    def can_manage_members(cls, user, project):
        return cls.can_manage(user, project)

    @classmethod
    def can_transfer_ownership(cls, user, project):
        membership = cls.membership(user, project)
        return bool(membership and membership.role == ProjectRoles.OWNER.value)

    @classmethod
    def allowed_actions(cls, user, project):
        actions = []
        if cls.can_view(user, project):
            actions += ['VIEW', 'VIEW_TASKS', 'COMMENT']
        if cls.can_manage(user, project):
            actions += ['EDIT', 'MANAGE_MEMBERS', 'ARCHIVE']
        if cls.can_transfer_ownership(user, project):
            actions.append('TRANSFER_OWNERSHIP')
        if not project.is_active and cls.can_manage(user, project):
            actions.append('RESTORE')
        return sorted(set(actions))
