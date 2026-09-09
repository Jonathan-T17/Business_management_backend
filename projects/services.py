from django.db import transaction
from django.core.exceptions import ValidationError
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from security.services import create_audit_log
from .models import Project, ProjectMembership
from .project_roles import ProjectRoles
from .access import ProjectAccess

class ProjectService:
    @staticmethod
    def _require_manage(user, project):
        if not ProjectAccess.can_manage(user, project):
            raise ValidationError('You do not have permission to manage this project.')

    @classmethod
    @transaction.atomic
    def create_project(cls, *, user, company, name, description='', branches=None, request=None):
        if user.company_id != company.id or not ProjectAccess.can_create(user):
            raise ValidationError('You do not have permission to create projects.')
        name = (name or '').strip()
        if not name:
            raise ValidationError({'name': 'Project name is required.'})
        if Project.objects.filter(company=company, name__iexact=name).exists():
            raise ValidationError({'name': 'A project with this name already exists in this company.'})
        project = Project.objects.create(company=company, name=name, description=description or '', created_by=user)
        if branches is not None:
            invalid = [b for b in branches if b.company_id != company.id or not b.is_active]
            if invalid:
                raise ValidationError({'branches': 'All project branches must be active branches in this company.'})
            project.branches.set(branches)
        ProjectMembership.objects.create(project=project, user=user, role=ProjectRoles.OWNER.value, added_by=user)
        create_audit_log(user=user, company=company, request=request, action='CREATE', description=f'Project created: {project.name}', obj=project)
        return project

    @classmethod
    @transaction.atomic
    def update_project(cls, *, project, user, validated_data, request=None):
        project = Project.objects.select_for_update().get(pk=project.pk)
        cls._require_manage(user, project)
        branches = validated_data.pop('branches', None)
        validated_data.pop('company', None); validated_data.pop('created_by', None); validated_data.pop('is_active', None)
        for field in ('name', 'description'):
            if field in validated_data:
                setattr(project, field, validated_data[field])
        project.full_clean(exclude=['branches'])
        project.save()
        if branches is not None:
            if any(b.company_id != project.company_id or not b.is_active for b in branches):
                raise ValidationError({'branches': 'Invalid project branch.'})
            project.branches.set(branches)
        create_audit_log(user=user, company=project.company, request=request, action='UPDATE', description=f'Project updated: {project.name}', obj=project)
        return project

    @classmethod
    @transaction.atomic
    def add_member(cls, *, project, user, member, role, request=None):
        project = Project.objects.select_for_update().get(pk=project.pk)
        cls._require_manage(user, project)
        if role == ProjectRoles.OWNER.value:
            raise ValidationError({'role': 'Use transfer ownership to assign a new owner.'})
        if role not in ProjectRoles.values():
            raise ValidationError({'role': 'Invalid project role.'})
        if member.company_id != project.company_id or not member.is_active or getattr(member, 'is_deleted', False):
            raise ValidationError({'user': 'Member must be an active user in this company.'})
        if project.branches.exists() and not project.branches.filter(pk=member.branch_id).exists():
            raise ValidationError({'user': 'Member must belong to one of this project’s branches.'})
        membership, created = ProjectMembership.objects.get_or_create(project=project, user=member, defaults={'role': role, 'added_by': user})
        if not created:
            raise ValidationError({'user': 'User is already a project member.'})
        create_audit_log(user=user, company=project.company, request=request, action='CREATE', description='Project member added.', obj=membership)
        return membership

    @classmethod
    @transaction.atomic
    def transfer_ownership(cls, *, project, new_owner, actor, request=None, reason=''):
        project = Project.objects.select_for_update().get(pk=project.pk)
        if not ProjectAccess.can_transfer_ownership(actor, project):
            raise ValidationError('Only the current project owner may transfer ownership.')
        if new_owner.company_id != project.company_id or not new_owner.is_active:
            raise ValidationError({'new_owner': 'New owner must be an active user in the same company.'})
        new_membership, _ = ProjectMembership.objects.select_for_update().get_or_create(
            project=project, user=new_owner,
            defaults={'role': ProjectRoles.MANAGER.value, 'added_by': actor},
        )
        current = ProjectMembership.objects.select_for_update().get(project=project, role=ProjectRoles.OWNER.value)
        if current.user_id == new_owner.id:
            return new_membership
        current.role = ProjectRoles.MANAGER.value
        current.save(update_fields=['role'])
        new_membership.role = ProjectRoles.OWNER.value
        new_membership.save(update_fields=['role'])
        create_audit_log(user=actor, company=project.company, request=request, action='UPDATE', description=f'Project ownership transferred. Reason: {reason}'.strip(), obj=project)
        return new_membership

    @classmethod
    @transaction.atomic
    def archive(cls, *, project, actor, request=None, reason=''):
        project = Project.objects.select_for_update().get(pk=project.pk)
        cls._require_manage(actor, project)
        if not project.is_active:
            return project
        project.is_active = False
        project.save(update_fields=['is_active'])
        create_audit_log(user=actor, company=project.company, request=request, action='UPDATE', description=f'Project archived. Reason: {reason}'.strip(), obj=project)
        return project

    @classmethod
    @transaction.atomic
    def restore(cls, *, project, actor, request=None):
        project = Project.objects.select_for_update().get(pk=project.pk)
        cls._require_manage(actor, project)
        project.is_active = True
        project.save(update_fields=['is_active'])
        create_audit_log(user=actor, company=project.company, request=request, action='UPDATE', description='Project restored.', obj=project)
        return project

    @classmethod
    @transaction.atomic
    def hard_delete_unused(cls, *, project, actor):
        project = Project.objects.select_for_update().get(pk=project.pk)
        cls._require_manage(actor, project)
        related = ('tasks', 'reports', 'comments', 'documents')
        if any(hasattr(project, rel) and getattr(project, rel).exists() for rel in related):
            raise ValidationError('Projects with business history cannot be permanently deleted. Archive it instead.')
        project.delete()
