from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Task, TaskActivity
from .access import TaskAccess
from security.services import create_audit_log

class TaskService:
    TRANSITIONS = {
        'pending': {'in_progress', 'blocked', 'done'},
        'in_progress': {'pending', 'blocked', 'done'},
        'blocked': {'pending', 'in_progress', 'done'},
        'done': {'in_progress'},
    }

    @staticmethod
    def _validate_assignees(project, assignees):
        for person in assignees or []:
            if person.company_id != project.company_id or not person.is_active or getattr(person, 'is_deleted', False):
                raise ValidationError({'assignees': 'Every assignee must be an active user in this company.'})
            if not project.memberships.filter(user=person).exists():
                raise ValidationError({'assignees': 'Every assignee must be a member of the project.'})

    @classmethod
    @transaction.atomic
    def create_task(cls, *, project, title, created_by, description='', status='pending', due_date=None, assignees=None, request=None):
        if not project.is_active or not TaskAccess.can_create(created_by, project):
            raise ValidationError('You cannot create tasks in this project.')
        cls._validate_assignees(project, assignees)
        task = Task.objects.create(company=project.company, project=project, title=title, description=description, created_by=created_by, status=status, due_date=due_date)
        if assignees is not None: task.assignees.set(assignees)
        cls.add_activity(task=task, user=created_by, action='TASK_CREATED', summary=f"Task '{task.title}' was created.")
        create_audit_log(user=created_by, company=task.company, request=request, action='CREATE', description='Task created.', obj=task)
        return task

    @classmethod
    @transaction.atomic
    def update_task(cls, *, task, validated_data, user, request=None):
        task = Task.objects.select_for_update().select_related('project').get(pk=task.pk)
        if not TaskAccess.can_manage(user, task):
            raise ValidationError('You do not have permission to manage this task.')
        validated_data.pop('company', None); validated_data.pop('created_by', None); validated_data.pop('project', None); validated_data.pop('is_active', None); validated_data.pop('status', None)
        assignees = validated_data.pop('assignees', None)
        if assignees is not None: cls._validate_assignees(task.project, assignees)
        for field in ('title','description','due_date'):
            if field in validated_data: setattr(task, field, validated_data[field])
        task.save()
        if assignees is not None:
            task.assignees.set(assignees)
            cls.add_activity(task=task, user=user, action='ASSIGNEES_UPDATED', summary='Task assignees were updated.')
        create_audit_log(user=user, company=task.company, request=request, action='UPDATE', description='Task updated.', obj=task)
        return task

    @classmethod
    @transaction.atomic
    def change_status(cls, *, task, status, actor, request=None):
        task = Task.objects.select_for_update().get(pk=task.pk)
        if not task.is_active or not TaskAccess.can_work(actor, task):
            raise ValidationError('You cannot change this task status.')
        if status not in dict(Task.STATUS_CHOICES): raise ValidationError({'status':'Invalid task status.'})
        if status == task.status: return task
        if status not in cls.TRANSITIONS.get(task.status, set()): raise ValidationError({'status':f'Cannot change task from {task.status} to {status}.'})
        old=task.status; task.status=status; task.save(update_fields=['status','updated_at'])
        cls.add_activity(task=task,user=actor,action='STATUS_CHANGED',summary=f'Task status changed from {old} to {status}.')
        create_audit_log(user=actor,company=task.company,request=request,action='UPDATE',description=f'Task status changed from {old} to {status}.',obj=task)
        return task

    @classmethod
    def complete(cls, **kwargs):
        return cls.change_status(status='done', **kwargs)

    @classmethod
    @transaction.atomic
    def set_active(cls, *, task, active, actor, request=None):
        task=Task.objects.select_for_update().get(pk=task.pk)
        if not TaskAccess.can_manage(actor, task): raise ValidationError('You do not have permission to manage this task.')
        task.is_active=active; task.save(update_fields=['is_active','updated_at'])
        cls.add_activity(task=task,user=actor,action='TASK_RESTORED' if active else 'TASK_DEACTIVATED',summary='Task restored.' if active else 'Task deactivated.')
        create_audit_log(user=actor,company=task.company,request=request,action='UPDATE',description='Task restored.' if active else 'Task deactivated.',obj=task)
        return task

    @staticmethod
    def add_activity(*, task, user, action, summary):
        return TaskActivity.objects.create(task=task,user=user,action=action,summary=summary)
