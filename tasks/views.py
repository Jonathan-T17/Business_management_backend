from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Task
from .serializers import TaskSerializer
from .permissions import IsProjectMember
from activity.models import ActivityLog

# Create your views here.
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        return Task.objects.filter(
            project__memberships__user=self.request.user,
            is_active=True
        ).distinct()

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)

        ActivityLog.objects.create(
            company=task.project.company,
            project=task.project,
            task=task,
            user=self.request.user,
            action="TASK_CREATED",
            metadata={"title": task.title}
        )

    def perform_update(self, serializer):
        task = serializer.save()

        ActivityLog.objects.create(
            company=task.project.company,
            project=task.project,
            task=task,
            user=self.request.user,
            action="TASK_UPDATED",
            metadata={"status": task.status}
        )