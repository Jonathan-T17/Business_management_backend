from django.db import models

# Create your models here.
from django.utils import timezone
from companies.models import Company, Branch
from projects.models import Project
from tasks.models import Task


class AIAnalyticsRecord(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="analytics"
    )

    level = models.CharField(
        max_length=20,
        choices=(
            ("COMPANY", "Company"),
            ("PROJECT", "Project"),
            ("USER", "User"),
        )
    )

    reference_id = models.PositiveIntegerField()
    summary = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)







class AnalyticsSnapshot(models.Model):

    SNAPSHOT_TYPE_CHOICES = (
        ("company", "Company"),
        ("branch", "Branch"),
        ("project", "Project"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="analytics_snapshots"
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    snapshot_type = models.CharField(
        max_length=20,
        choices=SNAPSHOT_TYPE_CHOICES
    )

    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)

    collaboration_score = models.FloatField(default=0.0)
    workload_balance_score = models.FloatField(default=0.0)

    ai_summary = models.TextField(blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]






class AIInsight(models.Model):

    INSIGHT_TYPES = (
        ("COMPANY_SUMMARY", "Company Summary"),
        ("PROJECT_SUMMARY", "Project Summary"),
        ("WORKLOAD_ALERT", "Workload Alert"),
        ("RISK_ALERT", "Risk Alert"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="ai_insights"
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_insights"
    )

    insight_type = models.CharField(
        max_length=30,
        choices=INSIGHT_TYPES
    )

    title = models.CharField(max_length=255)
    summary = models.TextField()

    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return self.title