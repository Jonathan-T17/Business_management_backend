from django.db import transaction

from .models import Task, TaskActivity


class TaskService:
    """
    Business logic for task management.
    """

    @staticmethod
    @transaction.atomic
    def create_task(
        *,
        project,
        title,
        description="",
        created_by,
        status=Task.STATUS_PENDING,
        due_date=None,
        assignees=None,
    ):
        task = Task.objects.create(
            company=project.company,
            project=project,
            title=title,
            description=description,
            created_by=created_by,
            status=status,
            due_date=due_date,
        )

        if assignees:
            task.assignees.set(assignees)

        TaskService.add_activity(
            task=task,
            user=created_by,
            action="TASK_CREATED",
            summary=f"Task '{task.title}' was created.",
        )

        return task

    @staticmethod
    @transaction.atomic
    def update_task(
        *,
        task,
        validated_data,
        user,
    ):
        old_status = task.status
        old_title = task.title
        old_due_date = task.due_date

        assignees = validated_data.pop(
            "assignees",
            None,
        )

        for field, value in validated_data.items():
            setattr(task, field, value)

        task.save()

        if assignees is not None:
            old_assignee_ids = set(
                task.assignees.values_list(
                    "id",
                    flat=True,
                )
            )

            new_assignee_ids = {
                user.id
                for user in assignees
            }

            task.assignees.set(assignees)

            if old_assignee_ids != new_assignee_ids:
                TaskService.add_activity(
                    task=task,
                    user=user,
                    action="ASSIGNEES_UPDATED",
                    summary="Task assignees were updated.",
                )

        if old_status != task.status:
            TaskService.add_activity(
                task=task,
                user=user,
                action="STATUS_CHANGED",
                summary=(
                    f"Task status changed from "
                    f"{old_status} to {task.status}."
                ),
            )

        if old_title != task.title:
            TaskService.add_activity(
                task=task,
                user=user,
                action="TITLE_UPDATED",
                summary="Task title was updated.",
            )

        if old_due_date != task.due_date:
            TaskService.add_activity(
                task=task,
                user=user,
                action="DUE_DATE_UPDATED",
                summary="Task due date was updated.",
            )

        TaskService.add_activity(
            task=task,
            user=user,
            action="TASK_UPDATED",
            summary=f"Task '{task.title}' was updated.",
        )

        return task

    @staticmethod
    @transaction.atomic
    def deactivate_task(
        *,
        task,
        user,
    ):
        task.is_active = False
        task.save(update_fields=[
            "is_active",
            "updated_at",
        ])

        TaskService.add_activity(
            task=task,
            user=user,
            action="TASK_DEACTIVATED",
            summary=f"Task '{task.title}' was deactivated.",
        )

        return task

    @staticmethod
    @transaction.atomic
    def restore_task(
        *,
        task,
        user,
    ):
        task.is_active = True
        task.save(update_fields=[
            "is_active",
            "updated_at",
        ])

        TaskService.add_activity(
            task=task,
            user=user,
            action="TASK_RESTORED",
            summary=f"Task '{task.title}' was restored.",
        )

        return task

    @staticmethod
    def add_activity(
        *,
        task,
        user,
        action,
        summary="",
    ):
        return TaskActivity.objects.create(
            task=task,
            user=user,
            action=action,
            summary=summary,
        )