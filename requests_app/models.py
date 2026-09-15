import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class BusinessRequest(models.Model):

    REQUEST_TYPES = (
        ("PURCHASE", "Purchase"),
        ("EQUIPMENT", "Equipment"),
        ("MAINTENANCE", "Maintenance"),
        ("BUDGET", "Budget"),
        ("STOCK", "Stock"),
        ("VEHICLE", "Vehicle"),
        ("LEAVE", "Leave"),
        ("TRAVEL", "Travel"),
        ("HR", "Human Resources"),
        ("OPERATIONAL", "Operational"),
        ("CUSTOM", "Custom"),
    )

    PRIORITY_CHOICES = (
        ("LOW", "Low"),
        ("NORMAL", "Normal"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    )

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("RETURNED", "Returned"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("FULFILLED", "Fulfilled"),
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
        related_name="business_requests",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_requests",
    )

    department = models.ForeignKey(
        "organizations.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_requests",
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_requests",
    )

    request_number = models.CharField(
        max_length=120,
        db_index=True,
    )

    request_type = models.CharField(max_length=100)

    request_type_definition = models.ForeignKey(
        "company_setup.RequestTypeDefinition", null=True, blank=True,
        on_delete=models.PROTECT, related_name="requests",
    )
    request_type_snapshot = models.JSONField(default=dict, blank=True)

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="NORMAL",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField()

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=10,
        default="RWF",
        blank=True,
    )

    quantity = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
    )

    needed_by = models.DateField(
        null=True,
        blank=True,
    )

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_requests",
    )

    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_requests",
    )

    form_submission = models.OneToOneField('forms_engine.FormSubmission', null=True, blank=True, on_delete=models.PROTECT, related_name='business_request')

    workflow = models.ForeignKey(
        "workflows.WorkflowDefinition",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="business_requests",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    fulfilled_at = models.DateTimeField(
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

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "request_number",
                ],
                name=
                    "unique_company_request_number",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                    "priority",
                ]
            )
        ]

    def __str__(self):
        return (
            f"{self.request_number} - "
            f"{self.title}"
        )
