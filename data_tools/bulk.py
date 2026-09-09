from django.core.exceptions import ValidationError
from django.db import transaction

from tasks.models import Task
from tasks.services import TaskService


class BulkTaskService:
    MAX_ITEMS = 500

    @classmethod
    @transaction.atomic
    def change_status(cls, *, user, task_ids, status):
        task_ids = list(dict.fromkeys(task_ids))
        if len(task_ids) > cls.MAX_ITEMS:
            raise ValidationError("Too many tasks selected.")
        if status not in dict(Task.STATUS_CHOICES):
            raise ValidationError("Invalid task status.")
        queryset = Task.objects.filter(company=user.company, id__in=task_ids)
        if queryset.count() != len(task_ids):
            raise ValidationError("One or more tasks are invalid or inaccessible.")
        for task in queryset.select_for_update():
            TaskService.update_task(task=task, validated_data={"status": status}, user=user)
        return len(task_ids)