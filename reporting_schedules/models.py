import uuid

from django.conf import settings
from django.db import models


class ReportingSchedule(models.Model):

    FREQUENCY_CHOICES = (
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("CUSTOM", "Custom"),
    )

    TARGET_TYPES = (
        ("USER", "Specific User"),
        ("ROLE", "System Role"),
        ("BRANCH", "Branch"),
        ("DEPARTMENT", "Department"),
        ("TEAM", "Team"),
        ("POSITION", "Position"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="reporting_schedules",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    template = models.ForeignKey(
        "forms_engine.FormTemplate",
        on_delete=models.PROTECT,
        related_name="reporting_schedules",
    )

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
    )

    target_type = models.CharField(
        max_length=20,
        choices=TARGET_TYPES,
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_reporting_schedules",
    )

    target_role = models.CharField(
        max_length=30,
        blank=True,
    )

    target_branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reporting_schedules",
    )

    target_department = models.ForeignKey(
        "organizations.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reporting_schedules",
    )

    target_team = models.ForeignKey(
        "organizations.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reporting_schedules",
    )

    target_position = models.ForeignKey(
        "organizations.Position",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reporting_schedules",
    )

    # DAILY
    due_time = models.TimeField(
        null=True,
        blank=True,
    )

    # WEEKLY: 0 Monday ... 6 Sunday
    weekday = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    # MONTHLY
    day_of_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    # CUSTOM future support
    custom_rule = models.JSONField(
        default=dict,
        blank=True,
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    allow_late_submission = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_reporting_schedules",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "name"
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "frequency",
                    "is_active",
                ]
            )
        ]

    def __str__(self):
        return self.name


class ReportingObligation(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("LATE", "Late"),
        ("MISSED", "Missed"),
        ("APPROVED", "Approved"),
        ("RETURNED", "Returned"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="reporting_obligations",
    )

    schedule = models.ForeignKey(
        ReportingSchedule,
        on_delete=models.CASCADE,
        related_name="obligations",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reporting_obligations",
    )

    reporting_date = models.DateField()

    due_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    submission = models.OneToOneField(
        "forms_engine.FormSubmission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reporting_obligation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    morning_reminder_sent = models.BooleanField(
        default=False,
    )

    final_reminder_sent = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = [
            "-due_at"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "schedule",
                    "user",
                    "reporting_date",
                ],
                name="unique_schedule_user_reporting_date",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                    "due_at",
                ]
            ),
            models.Index(
                fields=[
                    "user",
                    "status",
                    "due_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.schedule.name} - "
            f"{self.reporting_date}"
        )