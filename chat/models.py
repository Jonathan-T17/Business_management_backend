import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    COMPANY = "COMPANY"
    BRANCH = "BRANCH"
    DEPARTMENT = "DEPARTMENT"
    TEAM = "TEAM"
    PROJECT = "PROJECT"
    DIRECT = "DIRECT"

    SCOPE_CHOICES = (
        (COMPANY, "Company"),
        (BRANCH, "Branch"),
        (DEPARTMENT, "Department"),
        (TEAM, "Team"),
        (PROJECT, "Project"),
        (DIRECT, "Direct"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    name = models.CharField(max_length=255)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    department = models.ForeignKey(
        "organizations.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    team = models.ForeignKey(
        "organizations.Team",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "scope", "updated_at"]),
        ]


class ConversationMember(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_member",
            ),
        ]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_messages",
    )
    body = models.TextField()
    attachment_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]