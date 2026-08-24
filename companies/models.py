import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from core.roles import Roles


class Company(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    website = models.URLField(
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="companies_created",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    #communication fields

    email_from_name = models.CharField(
        max_length=255,
        blank=True,
    )
    
    email_reply_to = models.EmailField(
        blank=True,
    )
    
    email_footer = models.TextField(
        blank=True,
    )
    
    email_notifications_enabled = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    #communication properties
    @property
    def communication_name(self):
        return (
            self.email_from_name
            or self.name
        )
    
    @property
    def communication_reply_to(self):
        return (
            self.email_reply_to
            or self.email
            or ""
        )

class Branch(models.Model):
    company = models.ForeignKey(
        Company,
        related_name="branches",
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        max_length=255,
    )

    code = models.CharField(
        max_length=20,
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_branches",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="branches_created",
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
                fields=["company", "name"],
                name="unique_branch_name_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                condition=~Q(code=""),
                name="unique_branch_code_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class CompanyInvite(models.Model):
    STATUS = (
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("EXPIRED", "Expired"),
        ("REVOKED", "Revoked"),
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="invites",
    )

    email = models.EmailField()

    role = models.CharField(
        max_length=20,
        choices=Roles.choices(),
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING",
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_invites",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["company", "email", "status"],
            ),
            models.Index(
                fields=["token"],
            ),
        ]

    @property
    def is_valid(self):
        return (
            self.status == "PENDING"
            and self.expires_at > timezone.now()
            and self.company.is_active
        )

    def mark_expired_if_needed(self):
        if (
            self.status == "PENDING"
            and self.expires_at <= timezone.now()
        ):
            self.status = "EXPIRED"
            self.save(update_fields=["status"])
            return True

        return False

    def __str__(self):
        return f"{self.email} → {self.company.name}"