from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.roles import Roles


# ============================================================
# Workflow Definition
# ============================================================

class WorkflowDefinition(models.Model):

    TARGET_TYPES = (
        ("REPORT", "Report"),
        ("REQUEST", "Request"),
        ("FORM_SUBMISSION", "Form Submission"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="workflow_definitions",
    )

    name = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    target_type = models.CharField(
        max_length=30,
        choices=TARGET_TYPES,
        default="REPORT",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workflow_definitions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "code",
                ],
                name="unique_company_workflow_code",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "target_type",
                    "is_active",
                ]
            )
        ]

    def __str__(self):
        return (
            f"{self.company.name} - "
            f"{self.name}"
        )


# ============================================================
# Workflow Step Definition
# ============================================================

class WorkflowStepDefinition(models.Model):

    RECIPIENT_TYPES = (
        ("USER", "Specific User"),
        ("ROLE", "System Role"),
        ("POSITION", "Position"),
        ("REPORTER_MANAGER", "Reporter's Manager"),
        ("BRANCH_MANAGER", "Branch Manager"),
        ("DEPARTMENT_MANAGER", "Department Manager"),
        ("TEAM_LEADER", "Team Leader"),
        ("COMPANY_ADMIN", "Company Administrator"),
    )

    APPROVAL_MODES = (
        ("ANY", "Any Recipient"),
        ("ALL", "All Recipients"),
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    name = models.CharField(
        max_length=255,
    )

    order = models.PositiveIntegerField()

    recipient_type = models.CharField(
        max_length=30,
        choices=RECIPIENT_TYPES,
    )

    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    recipient_role = models.CharField(
        max_length=20,
        choices=Roles.choices(),
        blank=True,
    )

    recipient_position = models.ForeignKey(
        "organizations.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    approval_mode = models.CharField(
        max_length=10,
        choices=APPROVAL_MODES,
        default="ANY",
    )

    can_reject = models.BooleanField(
        default=True,
    )

    can_return = models.BooleanField(
        default=True,
    )

    notify_in_app = models.BooleanField(
        default=True,
    )

    notify_email = models.BooleanField(
        default=True,
    )

    is_required = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "workflow",
                    "order",
                ],
                name="unique_workflow_step_order",
            )
        ]

    def __str__(self):
        return (
            f"{self.workflow.name} "
            f"#{self.order} - {self.name}"
        )


# ============================================================
# Workflow Instance
# ============================================================

class WorkflowInstance(models.Model):
    workflow_version = models.PositiveIntegerField(default=1)

    STATUS_CHOICES = (
        ("IN_PROGRESS", "In Progress"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RETURNED", "Returned"),
        ("CANCELLED", "Cancelled"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="workflow_instances",
    )

    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="instances",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )

    object_id = models.CharField(
        max_length=64,
    )

    content_object = GenericForeignKey(
        "content_type",
        "object_id",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_workflows",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="IN_PROGRESS",
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-started_at"]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "content_type",
                    "object_id",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.workflow.name} - "
            f"{self.status}"
        )


# ============================================================
# Runtime Step
# ============================================================

class WorkflowStepInstance(models.Model):
    routing_snapshot = models.JSONField(default=dict, blank=True)

    STATUS_CHOICES = (
        ("WAITING", "Waiting"),
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RETURNED", "Returned"),
        ("SKIPPED", "Skipped"),
    )

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    definition_step = models.ForeignKey(
        WorkflowStepDefinition,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )

    order = models.PositiveIntegerField()

    name = models.CharField(
        max_length=255,
    )

    approval_mode = models.CharField(
        max_length=10,
        default="ANY",
    )

    can_reject = models.BooleanField(
        default=True,
    )

    can_return = models.BooleanField(
        default=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="WAITING",
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "workflow_instance",
                    "order",
                ],
                name="unique_runtime_workflow_step_order",
            )
        ]


# ============================================================
# Step Recipients
# ============================================================

class WorkflowStepRecipient(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RETURNED", "Returned"),
        ("SKIPPED", "Skipped"),
    )

    step = models.ForeignKey(
        WorkflowStepInstance,
        on_delete=models.CASCADE,
        related_name="recipients",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workflow_assignments",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    acted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "step",
                    "user",
                ],
                name="unique_workflow_step_recipient",
            )
        ]


# ============================================================
# Immutable Workflow Action History
# ============================================================

class WorkflowActionLog(models.Model):

    ACTION_CHOICES = (
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RETURNED", "Returned"),
        ("FORWARDED", "Forwarded"),
        ("CANCELLED", "Cancelled"),
    )

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )

    step = models.ForeignKey(
        WorkflowStepInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="action_logs",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflow_actions",
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
    )

    note = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
