from django.db import models
from django.conf import settings
from django.utils import timezone
from companies.models import Company
import uuid

User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ("TASK_ASSIGNED", "Task Assigned"),
        ("TASK_UPDATED", "Task Updated"),
        ("REPORT_CREATED", "Report Created"),
        ("REPORT_COMMENT", "Report Comment"),
        ("PROJECT_INVITE", "Project Invite"),
        ("SYSTEM", "System Notification"),
        ("AI_INSIGHT", "AI Insight"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    reference_id = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"