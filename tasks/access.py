from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from projects.access import ProjectAccess
from projects.project_roles import ProjectRoles

class TaskAccess:
    @staticmethod
    def membership(user, task):
        return ProjectAccess.membership(user, task.project)

    @classmethod
    def can_view(cls, user, task):
        return ProjectAccess.can_view(user, task.project)

    @classmethod
    def can_create(cls, user, project):
        membership = ProjectAccess.membership(user, project)
        return bool(membership and membership.role in (ProjectRoles.OWNER.value, ProjectRoles.MANAGER.value, ProjectRoles.CONTRIBUTOR.value))

    @classmethod
    def can_manage(cls, user, task):
        membership = cls.membership(user, task)
        return bool(membership and membership.role in (ProjectRoles.OWNER.value, ProjectRoles.MANAGER.value) and CapabilityService.has(user, Capabilities.MANAGE_TASKS))

    @classmethod
    def can_work(cls, user, task):
        membership = cls.membership(user, task)
        return bool(membership and (task.assignees.filter(pk=user.pk).exists() or membership.role in (ProjectRoles.OWNER.value, ProjectRoles.MANAGER.value)))

    @classmethod
    def allowed_actions(cls, user, task):
        actions=[]
        if cls.can_view(user, task): actions.append('VIEW')
        if cls.can_work(user, task) and task.is_active: actions += ['CHANGE_STATUS', 'COMPLETE', 'COMMENT']
        if cls.can_manage(user, task): actions += ['EDIT', 'REASSIGN', 'DEACTIVATE']
        if cls.can_manage(user, task) and not task.is_active: actions.append('RESTORE')
        return sorted(set(actions))
