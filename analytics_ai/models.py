import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from companies.models import Company, Branch
from projects.models import Project


User = settings.AUTH_USER_MODEL


class AIAnalyticsRecord(models.Model):
    """
    Stores generated analytics/AI summaries.

    This is the historical record of an analytics generation event.
    AnalyticsSnapshot stores structured numerical metrics, while this model
    stores the generated narrative/result.
    """

    LEVEL_CHOICES = (
        ("COMPANY", "Company"),
        ("BRANCH", "Branch"),
        ("PROJECT", "Project"),
        ("USER", "User"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="analytics_records",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analytics_records",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analytics_records",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analytics_records",
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
    )

    summary = models.TextField()

    metrics = models.JSONField(
        default=dict,
        blank=True,
    )

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-generated_at"]

        indexes = [
            models.Index(
                fields=["company", "-generated_at"],
                name="analytics_rec_company_date",
            ),
            models.Index(
                fields=["level", "-generated_at"],
                name="analytics_rec_level_date",
            ),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.level} - {self.generated_at}"


class AnalyticsSnapshot(models.Model):
    """
    Structured point-in-time analytics for company, branch or project.
    """

    SNAPSHOT_TYPE_CHOICES = (
        ("company", "Company"),
        ("branch", "Branch"),
        ("project", "Project"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analytics_snapshots",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="analytics_snapshots",
    )

    snapshot_type = models.CharField(
        max_length=20,
        choices=SNAPSHOT_TYPE_CHOICES,
    )

    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    pending_tasks = models.PositiveIntegerField(default=0)
    in_progress_tasks = models.PositiveIntegerField(default=0)
    blocked_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)

    total_projects = models.PositiveIntegerField(default=0)
    active_projects = models.PositiveIntegerField(default=0)

    total_reports = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)

    completion_rate = models.FloatField(default=0.0)
    overdue_rate = models.FloatField(default=0.0)

    collaboration_score = models.FloatField(default=0.0)
    workload_balance_score = models.FloatField(default=0.0)

    ai_summary = models.TextField(blank=True)

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-generated_at"]

        indexes = [
            models.Index(
                fields=["company", "snapshot_type", "-generated_at"],
                name="analytics_snap_company_type",
            ),
            models.Index(
                fields=["project", "-generated_at"],
                name="analytics_snap_project_date",
            ),
            models.Index(
                fields=["branch", "-generated_at"],
                name="analytics_snap_branch_date",
            ),
        ]

    def __str__(self):
        return (
            f"{self.company.name} - "
            f"{self.snapshot_type} - "
            f"{self.generated_at}"
        )


class AIInsight(models.Model):
    """
    Actionable analytics insight.

    The system currently generates deterministic/rule-based insights.
    A future AI provider can use the same model.
    """

    INSIGHT_TYPES = (
        ("COMPANY_SUMMARY", "Company Summary"),
        ("PROJECT_SUMMARY", "Project Summary"),
        ("BRANCH_SUMMARY", "Branch Summary"),
        ("USER_SUMMARY", "User Summary"),
        ("WORKLOAD_ALERT", "Workload Alert"),
        ("RISK_ALERT", "Risk Alert"),
        ("PERFORMANCE_ALERT", "Performance Alert"),
    )

    SEVERITY_CHOICES = (
        ("INFO", "Info"),
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    )

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("RESOLVED", "Resolved"),
        ("DISMISSED", "Dismissed"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="ai_insights",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_insights",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_insights",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_insights",
    )

    insight_type = models.CharField(
        max_length=30,
        choices=INSIGHT_TYPES,
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="INFO",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    title = models.CharField(max_length=255)

    summary = models.TextField()

    metrics = models.JSONField(
        default=dict,
        blank=True,
    )

    generated_at = models.DateTimeField(
        default=timezone.now,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-generated_at"]

        indexes = [
            models.Index(
                fields=["company", "-generated_at"],
                name="ai_insight_company_date",
            ),
            models.Index(
                fields=["company", "status"],
                name="ai_insight_company_status",
            ),
            models.Index(
                fields=["project", "-generated_at"],
                name="ai_insight_project_date",
            ),
            models.Index(
                fields=["branch", "-generated_at"],
                name="ai_insight_branch_date",
            ),
        ]

    def resolve(self):
        self.status = "RESOLVED"
        self.resolved_at = timezone.now()
        self.save(
            update_fields=["status", "resolved_at"]
        )

    def __str__(self):
        return self.title