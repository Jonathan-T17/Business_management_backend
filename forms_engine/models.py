from django.conf import settings
from django.contrib.contenttypes.fields import (
    GenericRelation,
)
from django.db import models
from django.utils import timezone

import uuid


# ============================================================
# Form Template
# ============================================================

class FormTemplate(models.Model):

    LIFECYCLE_CHOICES = (
        ("DRAFT", "Draft"),
        ("PUBLISHED", "Published"),
        ("ARCHIVED", "Archived"),
    )

    CATEGORY_CHOICES = (
        ("DAILY_REPORT", "Daily Report"),
        ("WEEKLY_REPORT", "Weekly Report"),
        ("MONTHLY_REPORT", "Monthly Report"),

        ("PRODUCTION", "Production"),
        ("DELIVERY", "Delivery"),
        ("COLLECTION", "Collection"),
        ("INSPECTION", "Inspection"),
        ("MAINTENANCE", "Maintenance"),
        ("FIELD_ACTIVITY", "Field Activity"),

        ("SALES", "Sales"),
        ("INCIDENT", "Incident"),
        ("REQUEST", "Request"),

        ("CUSTOM", "Custom"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="form_templates",
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

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default="CUSTOM",
    )

    # Optional organizational restriction
    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_templates",
    )

    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_templates",
    )

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_templates",
    )

    # Optional workflow automatically used when submitted
    workflow = models.ForeignKey(
        "workflows.WorkflowDefinition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_templates",
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    is_active = models.BooleanField(
        default=True,
    )

    lifecycle_status = models.CharField(
        max_length=20,
        choices=LIFECYCLE_CHOICES,
        default="DRAFT",
    )

    allow_drafts = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_form_templates",
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

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "code",
                ],
                name="unique_company_form_template_code",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "category",
                    "is_active",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.company.name} - "
            f"{self.name}"
        )


# ============================================================
# Form Field Definition
# ============================================================

class FormField(models.Model):

    FIELD_TYPES = (
        ("TEXT", "Text"),
        ("LONG_TEXT", "Long Text"),

        ("INTEGER", "Integer"),
        ("DECIMAL", "Decimal"),

        ("BOOLEAN", "Boolean"),

        ("DATE", "Date"),
        ("TIME", "Time"),
        ("DATETIME", "Date & Time"),

        ("SELECT", "Select"),
        ("MULTISELECT", "Multi Select"),

        ("EMAIL", "Email"),
        ("PHONE", "Phone"),

        ("LOCATION", "Location"),
    )

    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    key = models.SlugField(
        max_length=100,
    )

    label = models.CharField(
        max_length=255,
    )

    help_text = models.CharField(
        max_length=500,
        blank=True,
    )

    field_type = models.CharField(
        max_length=30,
        choices=FIELD_TYPES,
    )

    required = models.BooleanField(
        default=False,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    # Used by SELECT / MULTISELECT.
    # Example:
    # [
    #   {"value": "MORNING", "label": "Morning"},
    #   {"value": "EVENING", "label": "Evening"}
    # ]
    options = models.JSONField(
        default=list,
        blank=True,
    )

    # Generic validation configuration.
    # Examples:
    # {
    #     "min": 0,
    #     "max": 5000
    # }
    #
    # or:
    # {
    #     "min_length": 5,
    #     "max_length": 200
    # }
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
    )

    placeholder = models.CharField(
        max_length=255,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = [
            "order",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "template",
                    "key",
                ],
                name="unique_form_field_key",
            )
        ]

    def __str__(self):
        return (
            f"{self.template.name}: "
            f"{self.label}"
        )


# ============================================================
# Form Submission
# ============================================================

class FormSubmission(models.Model):

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("RETURNED", "Returned"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("CLOSED", "Closed"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="form_submissions",
    )

    template = models.ForeignKey(
        FormTemplate,
        on_delete=models.PROTECT,
        related_name="submissions",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="form_submissions",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    # Optional links only.
    # A submission does NOT require a project/task.
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_submissions",
    )

    attachments = GenericRelation(
        "documents.Attachment",
        related_query_name="form_submissions",
    )

    reference_number = models.CharField(
        max_length=120,
    )

    title = models.CharField(
        max_length=255,
        blank=True,
    )

    reporting_date = models.DateField(
        default=timezone.localdate,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    # Dynamic submitted form values.
    data = models.JSONField(
        default=dict,
    )

    # Very important:
    # preserves what the form looked like when submitted,
    # even if ADMIN changes the template later.
    schema_snapshot = models.JSONField(
        default=dict,
        blank=True,
    )

    template_version = models.PositiveIntegerField(
        default=1,
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
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
                    "reporting_date",
                ]
            ),

            models.Index(
                fields=[
                    "company",
                    "branch",
                    "reporting_date",
                ]
            ),

            models.Index(
                fields=[
                    "template",
                    "reporting_date",
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "reference_number",
                ],
                name="unique_company_form_submission_reference",
            )
        ]

    def __str__(self):
        return (
            f"{self.reference_number} - "
            f"{self.template.name}"
        )