import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class FieldActivity(models.Model):

    ACTIVITY_TYPES = (
        ("DELIVERY", "Delivery"),
        ("COLLECTION", "Collection"),
        ("INSPECTION", "Inspection"),
        ("MAINTENANCE", "Maintenance"),
        ("SALES_VISIT", "Sales Visit"),
        ("SERVICE_VISIT", "Service Visit"),
        ("SITE_VISIT", "Site Visit"),
        ("ROUTE", "Route"),
        ("OTHER", "Other"),
    )

    STATUS_CHOICES = (
        ("PLANNED", "Planned"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
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
        related_name="field_activities",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="field_activities",
    )

    department = models.ForeignKey(
        "organizations.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="field_activities",
    )

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="field_activities",
    )

    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPES,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    activity_date = models.DateField(
        default=timezone.localdate,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PLANNED",
    )

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="field_activities",
    )

    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="field_activities",
    )

    vehicle_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    started_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    started_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    completed_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    completed_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_field_activities",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-activity_date",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "activity_date",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "employee",
                    "activity_date",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.title} - "
            f"{self.employee.email}"
        )


class FieldStop(models.Model):

    STOP_TYPES = (
        ("DELIVERY", "Delivery"),
        ("COLLECTION", "Collection"),
        ("INSPECTION", "Inspection"),
        ("SERVICE", "Service"),
        ("CUSTOMER_VISIT", "Customer Visit"),
        ("SITE", "Site"),
        ("OTHER", "Other"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ARRIVED", "Arrived"),
        ("COMPLETED", "Completed"),
        ("SKIPPED", "Skipped"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    activity = models.ForeignKey(
        FieldActivity,
        on_delete=models.CASCADE,
        related_name="stops",
    )

    sequence = models.PositiveIntegerField(
        default=1,
    )

    stop_type = models.CharField(
        max_length=30,
        choices=STOP_TYPES,
    )

    client_name = models.CharField(
        max_length=255,
        blank=True,
    )

    location_name = models.CharField(
        max_length=255,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    contact_name = models.CharField(
        max_length=255,
        blank=True,
    )

    contact_phone = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    planned_arrival = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    form_submission = models.OneToOneField(
        "forms_engine.FormSubmission",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="field_stop",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "sequence",
            "created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "activity",
                    "sequence",
                ],
                name="unique_field_stop_sequence",
            )
        ]

    def __str__(self):
        return (
            f"{self.activity.title} "
            f"Stop {self.sequence}"
        )


class FieldStopMetric(models.Model):

    stop = models.ForeignKey(
        FieldStop,
        on_delete=models.CASCADE,
        related_name="metrics",
    )

    key = models.CharField(
        max_length=100,
    )

    label = models.CharField(
        max_length=255,
    )

    numeric_value = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        null=True,
        blank=True,
    )

    text_value = models.CharField(
        max_length=500,
        blank=True,
    )

    unit = models.CharField(
        max_length=50,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "stop",
                    "key",
                ],
                name="unique_field_stop_metric",
            )
        ]

    def __str__(self):
        return (
            f"{self.stop} - "
            f"{self.label}"
        )