import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
)
from django.contrib.contenttypes.models import (
    ContentType,
)
from django.db import models


# ============================================================
# Generic Attachment
# ============================================================

def attachment_upload_path(
    instance,
    filename,
):
    ext = os.path.splitext(
        filename
    )[1].lower()

    safe_name = (
        f"{uuid.uuid4().hex}{ext}"
    )

    company_id = (
        instance.company_id
        or "platform"
    )

    return (
        f"attachments/"
        f"{company_id}/"
        f"{safe_name}"
    )


class Attachment(models.Model):

    TYPE_CHOICES = (
        ("FILE", "File"),
        ("IMAGE", "Image"),
        ("PHOTO", "Photo"),
        ("RECEIPT", "Receipt"),
        ("INVOICE", "Invoice"),
        ("DELIVERY_NOTE", "Delivery Note"),
        ("SIGNATURE", "Signature"),
        ("EVIDENCE", "Evidence"),
        ("OTHER", "Other"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_attachments",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    object_id = models.CharField(
        max_length=64,
    )

    content_object = GenericForeignKey(
        "content_type",
        "object_id",
    )

    attachment_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="FILE",
    )

    file = models.FileField(
        upload_to=
            attachment_upload_path,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    mime_type = models.CharField(
        max_length=150,
        blank=True,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    description = models.CharField(
        max_length=500,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "content_type",
                    "object_id",
                ]
            ),
            models.Index(
                fields=[
                    "company",
                    "attachment_type",
                    "is_active",
                ]
            ),
        ]

    def __str__(self):
        return self.original_filename


# ============================================================
# Document Category
# ============================================================

class DocumentCategory(models.Model):

    VISIBILITY_CHOICES = (
        ("COMPANY", "Company"),
        ("BRANCH", "Branch"),
        ("DEPARTMENT", "Department"),
        ("TEAM", "Team"),
        ("MANAGEMENT", "Management"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="document_categories",
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    default_visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="COMPANY",
    )

    sensitive = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "name"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "company",
                    "name",
                ],
                name=
                    "unique_company_document_category",
            )
        ]

    def __str__(self):
        return self.name


# ============================================================
# Managed Document
# ============================================================

def document_upload_path(
    instance,
    filename,
):
    ext = os.path.splitext(
        filename
    )[1].lower()

    safe_name = (
        f"{uuid.uuid4().hex}{ext}"
    )

    return (
        f"documents/"
        f"{instance.document.company_id}/"
        f"{safe_name}"
    )


class Document(models.Model):

    VISIBILITY_CHOICES = (
        ("PRIVATE", "Private"),
        ("COMPANY", "Company"),
        ("BRANCH", "Branch"),
        ("DEPARTMENT", "Department"),
        ("TEAM", "Team"),
        ("MANAGEMENT", "Management"),
    )

    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("ARCHIVED", "Archived"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    department = models.ForeignKey(
        "organizations.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    document_number = models.CharField(
        max_length=100,
        blank=True,
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default="COMPANY",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )

    current_version = models.PositiveIntegerField(
        default=1,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="owned_documents",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_documents",
    )

    effective_date = models.DateField(
        null=True,
        blank=True,
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-updated_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "visibility",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "company",
                    "category",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return self.title


# ============================================================
# Document Version
# ============================================================

class DocumentVersion(models.Model):

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    version_number = models.PositiveIntegerField()

    file = models.FileField(
        upload_to=
            document_upload_path,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    mime_type = models.CharField(
        max_length=150,
        blank=True,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    change_note = models.TextField(
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name=
            "uploaded_document_versions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-version_number"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "document",
                    "version_number",
                ],
                name=
                    "unique_document_version",
            )
        ]

    def __str__(self):
        return (
            f"{self.document.title} "
            f"v{self.version_number}"
        )