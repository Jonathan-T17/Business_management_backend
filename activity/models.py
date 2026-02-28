from django.conf import settings
from django.db import models
from companies.models import Company
from projects.models import Project
from tasks.models import Task

# Create your models here.

User = settings.AUTH_USER_MODEL


class ActivityLog(models.Model):

    ACTION_CHOICES = (
        ("TASK_CREATED", "Task Created"),
        ("TASK_UPDATED", "Task Updated"),
        ("STATUS_CHANGED", "Status Changed"),
        ("COMMENT_ADDED", "Comment Added"),
        ("TASK_ASSIGNED", "Task Assigned"),
        ("PROJECT_CREATED", "Project Created"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]