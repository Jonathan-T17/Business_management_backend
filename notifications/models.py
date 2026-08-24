import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class Notification(models.Model):
    """
    Stores in-app notifications for authenticated users.

    Notifications are tenant-scoped through the company relationship
    and recipient relationship.
    """

    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"

    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_UPDATED = "PROJECT_UPDATED"
    PROJECT_DELETED = "PROJECT_DELETED"
    PROJECT_INVITE = "PROJECT_INVITE"
    OWNERSHIP_TRANSFERRED = "OWNERSHIP_TRANSFERRED"

    MEMBERSHIP_CREATED = "MEMBERSHIP_CREATED"
    MEMBERSHIP_UPDATED = "MEMBERSHIP_UPDATED"
    ROLE_CHANGED = "ROLE_CHANGED"

    REPORT_CREATED = "REPORT_CREATED"
    REPORT_SUBMITTED = "REPORT_SUBMITTED"
    REPORT_COMMENT = "REPORT_COMMENT"

    COMMENT_ADDED = "COMMENT_ADDED"
    COMMENT_REPLY = "COMMENT_REPLY"

    INVITATION = "INVITATION"

    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AI_INSIGHT = "AI_INSIGHT"

    NOTIFICATION_TYPES = (
        (TASK_ASSIGNED, "Task Assigned"),
        (TASK_CREATED, "Task Created"),
        (TASK_UPDATED, "Task Updated"),
        (TASK_DELETED, "Task Deleted"),

        (PROJECT_CREATED, "Project Created"),
        (PROJECT_UPDATED, "Project Updated"),
        (PROJECT_DELETED, "Project Deleted"),
        (PROJECT_INVITE, "Project Invitation"),
        (OWNERSHIP_TRANSFERRED, "Project Ownership Transferred"),

        (MEMBERSHIP_CREATED, "Project Membership Created"),
        (MEMBERSHIP_UPDATED, "Project Membership Updated"),
        (ROLE_CHANGED, "Project Role Changed"),

        (REPORT_CREATED, "Report Created"),
        (REPORT_SUBMITTED, "Report Submitted"),
        (REPORT_COMMENT, "Report Comment"),

        (COMMENT_ADDED, "Comment Added"),
        (COMMENT_REPLY, "Comment Reply"),

        (INVITATION, "Company Invitation"),

        (SECURITY, "Security Event"),
        (SYSTEM, "System Notification"),
        (AI_INSIGHT, "AI Insight"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=40,
        choices=NOTIFICATION_TYPES,
        default=SYSTEM,
    )

    title = models.CharField(
        max_length=255,
    )

    message = models.TextField()

    reference_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    url = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recipient_read_idx",
            ),
            models.Index(
                fields=["company", "-created_at"],
                name="notif_company_created_idx",
            ),
            models.Index(
                fields=["notification_type", "-created_at"],
                name="notif_type_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"

    @property
    def is_unread(self):
        return not self.is_read




#communication  inside the company
class NotificationPreference(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    in_app_enabled = models.BooleanField(
        default=True
    )

    email_enabled = models.BooleanField(
        default=True
    )

    task_assignments = models.BooleanField(
        default=True
    )

    task_updates = models.BooleanField(
        default=False
    )

    project_updates = models.BooleanField(
        default=True
    )

    reports = models.BooleanField(
        default=True
    )

    comments = models.BooleanField(
        default=False
    )

    organization_updates = models.BooleanField(
        default=True
    )

    subscription_updates = models.BooleanField(
        default=True
    )

    ai_insights = models.BooleanField(
        default=False
    )

    digest_enabled = models.BooleanField(
        default=False
    )

    digest_cadence = models.CharField(
        max_length=10,
        choices=[("DAILY", "Daily"), ("WEEKLY", "Weekly"), ("NONE", "None")],
        default="DAILY",
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"Notification preferences "
            f"for {self.user.email}"
        )


class EmailDeliveryLog(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_delivery_logs",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="email_delivery_logs",
    )

    recipient_email = models.EmailField()

    email_type = models.CharField(
        max_length=80
    )

    subject = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    reference_id = models.CharField(
        max_length=255,
        blank=True,
    )

    error_message = models.TextField(
        blank=True
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "recipient_email",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.email_type} → "
            f"{self.recipient_email}"
        )