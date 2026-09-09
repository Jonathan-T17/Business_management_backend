import uuid

from django.conf import settings
from django.db import models


class CompanyPlan(models.Model):

    PLAN_TYPES = (
        ("ANNUAL", "Annual"),
        ("QUARTERLY", "Quarterly"),
        ("MONTHLY", "Monthly"),
        ("WEEKLY", "Weekly"),
        ("BRANCH", "Branch"),
        ("DEPARTMENT", "Department"),
        ("CUSTOM", "Custom"),
    )

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("ARCHIVED", "Archived"),
    )

    VISIBILITY_CHOICES = (
        ("PRIVATE", "Private"),
        ("MANAGEMENT", "Management"),
        ("COMPANY", "Company"),
        ("BRANCH", "Branch"),
        ("DEPARTMENT", "Department"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="company_plans",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plans",
    )

    department = models.ForeignKey(
        "organizations.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plans",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="MANAGEMENT",
    )

    start_date = models.DateField()

    end_date = models.DateField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_company_plans",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_company_plans",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-start_date"
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                    "start_date",
                ]
            )
        ]

    def __str__(self):
        return self.title


class PlanItem(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("BLOCKED", "Blocked"),
        ("CANCELLED", "Cancelled"),
    )

    plan = models.ForeignKey(
        CompanyPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_plan_items",
    )

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plan_items",
    )

    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plan_items",
    )

    target_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    actual_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

    def __str__(self):
        return self.title