from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.audit import ActivityAudit
from core.tenant import TenantService
from notifications.services import CommunicationService, create_notification

from security.viewsets import SecureModelViewSet

from .models import Task, TaskActivity
from .serializers import (
    TaskSerializer,
    TaskActivitySerializer,
)
from .services import TaskService
from .permissions import (IsTaskMember,CanManageTask)


class TaskViewSet(SecureModelViewSet):

    queryset = Task.objects.all()

    serializer_class = TaskSerializer

    permission_classes = [
        IsAuthenticated,
        IsTaskMember,
    ]

    audit_action = "TASK"

    def get_queryset(self):

        queryset = TenantService.tasks(
            self.request.user
        )

        return queryset.select_related(
            "company",
            "project",
            "created_by",
        ).prefetch_related(
            "assignees",
            "project__memberships",
        )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
            "stats",
        ):
            return [
                IsAuthenticated(),
                IsTaskMember(),
            ]

        return [
            IsAuthenticated(),
            CanManageTask(),
        ]

    def perform_create(self, serializer):

        task = serializer.save(
            company=self.request.user.company,
            created_by=self.request.user,
        )

        # Ensure company always follows project.
        if task.project.company_id != task.company_id:
            task.company = task.project.company
            task.save(
                update_fields=[
                    "company",
                    "updated_at",
                ]
            )

        TaskService.add_activity(
            task=task,
            user=self.request.user,
            action="TASK_CREATED",
            summary=(
                f"Task '{task.title}' was created."
            ),
        )

        ActivityAudit.log(
            user=self.request.user,
            company=task.company,
            project=task.project,
            task=task,
            action="TASK_CREATED",
            metadata={
                "title": task.title,
                "status": task.status,
            },
        )

        self._notify_project_members(
            task=task,
            notification_type="TASK_CREATED",
            title="New Task Created",
            message=(
                f"A new task '{task.title}' was created "
                f"in project '{task.project.name}'."
            ),
        )

    def perform_update(self, serializer):

        task = self.get_object()

        old_status = task.status
        old_assignee_ids = set(
            task.assignees.values_list(
                "id",
                flat=True,
            )
        )

        task = serializer.save()

        # Company must never be changed through API input.
        if task.company_id != task.project.company_id:
            task.company = task.project.company
            task.save(
                update_fields=[
                    "company",
                    "updated_at",
                ]
            )

        new_assignee_ids = set(
            task.assignees.values_list(
                "id",
                flat=True,
            )
        )

        ActivityAudit.log(
            user=self.request.user,
            company=task.company,
            project=task.project,
            task=task,
            action="TASK_UPDATED",
            metadata={
                "title": task.title,
                "old_status": old_status,
                "new_status": task.status,
            },
        )

        TaskService.add_activity(
            task=task,
            user=self.request.user,
            action="TASK_UPDATED",
            summary=(
                f"Task '{task.title}' was updated."
            ),
        )

        if old_status != task.status:
            TaskService.add_activity(
                task=task,
                user=self.request.user,
                action="STATUS_CHANGED",
                summary=(
                    f"Status changed from "
                    f"{old_status} to {task.status}."
                ),
            )

        if old_assignee_ids != new_assignee_ids:

            TaskService.add_activity(
                task=task,
                user=self.request.user,
                action="ASSIGNEES_UPDATED",
                summary="Task assignees were updated.",
            )

            # self._notify_assignees(
            #     task=task,
            #     old_assignee_ids=old_assignee_ids,
            # )
            def _notify_assignees(self, *, task, old_assignee_ids):
                #find only newly assigned users
                new_assignees = task.assignees.exclude(id__in=old_assignee_ids)

                for recipient in new_assignees:
                    CommunicationService.send(
                        recipient=recipient,
                        company=task.company,
                        notification_type="TASK_ASSIGNED",
                        title="New task assigned",
                        message=f"You have been assigned '{task.title}'.",
                        reference_id=str(task.id),
                        url=f"/tasks/{task.id}",
                        send_email=True,
                        email_subject=f"New task assigned: {task.title}",
                        email_template="emails/task_assigned.html",
                        email_context={
                            "task": task,
                            "assigned_by": self.request.user,
                            "action_url": f"{settings.FRONTEND_URL}/tasks/{task.id}",
                        },
                    )

        self._notify_project_members(
            task=task,
            notification_type="TASK_UPDATED",
            title="Task Updated",
            message=(
                f"Task '{task.title}' in project "
                f"'{task.project.name}' was updated."
            ),
        )

    def perform_destroy(self, instance):

        task = instance

        TaskService.deactivate_task(
            task=task,
            user=self.request.user,
        )

        ActivityAudit.log(
            user=self.request.user,
            company=task.company,
            project=task.project,
            task=task,
            action="TASK_DELETED",
            metadata={
                "title": task.title,
            },
        )

        self._notify_project_members(
            task=task,
            notification_type="TASK_DELETED",
            title="Task Deactivated",
            message=(
                f"Task '{task.title}' in project "
                f"'{task.project.name}' was deactivated."
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):

        task = self.get_object()

        TaskService.restore_task(
            task=task,
            user=request.user,
        )

        ActivityAudit.log(
            user=request.user,
            company=task.company,
            project=task.project,
            task=task,
            action="TASK_RESTORED",
            metadata={
                "title": task.title,
            },
        )

        return Response(
            TaskSerializer(
                task,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(self, request, pk=None):

        task = self.get_object()

        task.status = Task.STATUS_DONE
        task.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        TaskService.add_activity(
            task=task,
            user=request.user,
            action="TASK_COMPLETED",
            summary=(
                f"Task '{task.title}' was completed."
            ),
        )

        ActivityAudit.log(
            user=request.user,
            company=task.company,
            project=task.project,
            task=task,
            action="TASK_COMPLETED",
            metadata={
                "title": task.title,
            },
        )

        self._notify_project_members(
            task=task,
            notification_type="TASK_COMPLETED",
            title="Task Completed",
            message=(
                f"Task '{task.title}' has been completed."
            ),
        )

        return Response(
            TaskSerializer(
                task,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="stats",
    )
    def stats(self, request):

        tasks = self.get_queryset()

        today = timezone.localdate()

        data = tasks.aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(
                    status=Task.STATUS_DONE
                ),
            ),
            pending=Count(
                "id",
                filter=Q(
                    status=Task.STATUS_PENDING
                ),
            ),
            in_progress=Count(
                "id",
                filter=Q(
                    status=Task.STATUS_IN_PROGRESS
                ),
            ),
            blocked=Count(
                "id",
                filter=Q(
                    status=Task.STATUS_BLOCKED
                ),
            ),
            overdue=Count(
                "id",
                filter=Q(
                    due_date__lt=today
                ) & ~Q(
                    status=Task.STATUS_DONE
                ),
            ),
        )

        return Response(data)

    def _notify_project_members(
        self,
        *,
        task,
        notification_type,
        title,
        message,
    ):

        memberships = task.project.memberships.select_related(
            "user"
        ).exclude(
            user=self.request.user
        )

        for membership in memberships:

            create_notification(
                recipient=membership.user,
                company=task.company,
                notification_type=notification_type,
                title=title,
                message=message,
                reference_id=str(task.id),
            )

    def _notify_assignees(
        self,
        *,
        task,
        old_assignee_ids,
    ):

        current_assignees = task.assignees.all()

        for assignee in current_assignees:

            if assignee.id in old_assignee_ids:
                continue

            create_notification(
                recipient=assignee,
                company=task.company,
                notification_type="TASK_ASSIGNED",
                title="Task Assigned",
                message=(
                    f"You have been assigned "
                    f"'{task.title}'."
                ),
                reference_id=str(task.id),
            )


class TaskActivityViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = TaskActivitySerializer

    permission_classes = [
        IsAuthenticated,
        IsTaskMember,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = TaskActivity.objects.select_related(
            "task",
            "task__company",
            "task__project",
            "user",
        )

        if user.role == "SUPERUSER":
            return queryset

        return queryset.filter(
            task__company=user.company,
            task__project__memberships__user=user,
        ).distinct()