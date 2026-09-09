from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import UserManager
from django.utils import timezone
import uuid
from core.roles import Roles


class User(AbstractBaseUser, PermissionsMixin):
    ACCOUNT_STATES = (
        ("PENDING_VERIFICATION", "Pending verification"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("DEACTIVATED", "Deactivated"),
        ("TERMINATED", "Terminated"),
    )

    role = models.CharField(
        max_length=20,
        choices=Roles.choices(),
        default=Roles.INDIVIDUAL,
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    phone_number = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    user_timezone = models.CharField(max_length=100, default="UTC")
    preferred_language = models.CharField(max_length=20, default="en")
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    must_change_password = models.BooleanField(
        default=False,
    )
    password_reset_required_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    branch = models.ForeignKey(
        'companies.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    account_state = models.CharField(
        max_length=30,
        choices=ACCOUNT_STATES,
        default="PENDING_VERIFICATION",
        db_index=True,
    )
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Django Admin is a platform/internal surface. Tenant ADMIN does not
        # automatically receive Django-admin access.
        if self.role == Roles.SUPERUSER or self.is_superuser:
            self.is_staff = True
        super().save(*args, **kwargs)

    # ✅ Soft delete helpers
    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "is_active", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.is_active = False
        self.account_state = "DEACTIVATED"
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "is_active", "account_state", "deleted_at"])

    # ✅ Role helpers
    @property
    def is_company_admin(self):
        return self.role == Roles.ADMIN

    @property
    def is_manager(self):
        return self.role == Roles.MANAGER

    @property
    def is_employee(self):
        return self.role == Roles.EMPLOYEE

    @property
    def is_individual(self):
        return self.role == Roles.INDIVIDUAL

