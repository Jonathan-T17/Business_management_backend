import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class OfficialRecord(models.Model):

    RECORD_TYPES = (
        ("REPORT", "Report"),
        ("REQUEST", "Request"),
        ("FORM_SUBMISSION", "Form Submission"),
        ("PLAN", "Plan"),
        ("FIELD_SUMMARY", "Field Summary"),
        ("OTHER", "Other"),
    )

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("SUPERSEDED", "Superseded"),
        ("VOID", "Void"),
        ("ARCHIVED", "Archived"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    verification_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.PROTECT,
        related_name="official_records",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="official_records",
    )

    record_type = models.CharField(
        max_length=30,
        choices=RECORD_TYPES,
    )

    record_number = models.CharField(
        max_length=120,
    )

    title = models.CharField(
        max_length=255,
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
    )

    object_id = models.CharField(
        max_length=64,
    )

    source_object = GenericForeignKey(
        "content_type",
        "object_id",
    )

    source_version = models.PositiveIntegerField(
        default=1,
    )

    snapshot = models.JSONField(
        default=dict,
    )

    approval_snapshot = models.JSONField(
        default=list,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    void_reason = models.TextField(
        blank=True,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="voided_official_records",
    )

    issued_at = models.DateTimeField()

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="issued_official_records",
    )

    supersedes = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replacement_records",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-issued_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "record_number",
                ],
                name="unique_official_record_number",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "record_type",
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
        return self.record_number




class RecordExport(models.Model):
    
    FORMAT_CHOICES = (
        ("PDF", "PDF"),
        ("PRINT", "Print"),
        ("CSV", "CSV"),
        ("XLSX", "Excel"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="record_exports",
    )

    record = models.ForeignKey(
        OfficialRecord,
        on_delete=models.CASCADE,
        related_name="exports",
    )

    export_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
    )

    exported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="record_exports",
    )

    purpose = models.CharField(
        max_length=255,
        blank=True,
    )

    exported_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-exported_at"]





class RecordSequence(models.Model):
    
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="record_sequences",
    )

    prefix = models.CharField(
        max_length=30,
    )

    year = models.PositiveIntegerField()

    last_number = models.PositiveBigIntegerField(
        default=0,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "prefix",
                    "year",
                ],
                name="unique_record_sequence",
            )
        ]