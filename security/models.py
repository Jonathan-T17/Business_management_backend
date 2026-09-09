import hashlib
import hmac
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    STATUS_CHOICES = (("SUCCESS", "Success"), ("FAILED", "Failed"))
    SEVERITY_CHOICES = (("INFO", "Info"), ("WARNING", "Warning"), ("CRITICAL", "Critical"))
    ACTOR_CHOICES = (("USER", "User"), ("SYSTEM", "System"), ("API", "API"), ("PLATFORM", "Platform"), ("SUPPORT", "Support"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    action = models.CharField(max_length=120, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="INFO", db_index=True)
    actor_type = models.CharField(max_length=20, choices=ACTOR_CHOICES, default="USER")
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUCCESS")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["company", "action", "severity"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise RuntimeError("AuditLog is immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog cannot be deleted through application code.")


class ActiveSession(models.Model):
    TERMINATION_REASONS = (("LOGOUT", "Logout"), ("ADMIN", "Administrator"), ("PASSWORD_RESET", "Password reset"), ("ACCOUNT_STATE", "Account state"), ("SECURITY", "Security"), ("EXPIRED", "Expired"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="active_sessions")
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.SET_NULL, related_name="active_sessions")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="active_sessions")
    refresh_token_jti = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    browser = models.CharField(max_length=255, blank=True)
    operating_system = models.CharField(max_length=255, blank=True)
    device = models.CharField(max_length=255, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    terminated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="terminated_sessions")
    termination_reason = models.CharField(max_length=30, choices=TERMINATION_REASONS, blank=True)
    termination_note = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_activity"]
        indexes = [models.Index(fields=["user", "is_active"]), models.Index(fields=["company", "is_active"])]


class LoginHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_history")
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.SET_NULL, related_name="login_history")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="login_history")
    session = models.ForeignKey(ActiveSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="login_history")
    email_hash = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=255, blank=True)
    operating_system = models.CharField(max_length=255, blank=True)
    device = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)  # coarse security context only
    successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "created_at"]), models.Index(fields=["successful", "created_at"])]


class FailedLoginAttempt(models.Model):
    email_hash = models.CharField(max_length=64, db_index=True)
    email_hint = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField()
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.SET_NULL, related_name="failed_login_attempts")
    attempts = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    locked_by_system = models.BooleanField(default=True)
    last_attempt_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["email_hash", "ip_address"], name="unique_failed_login_principal_ip")]
        indexes = [models.Index(fields=["email_hash", "ip_address"]), models.Index(fields=["locked_until"])]


class TrustedDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trusted_devices")
    token_hash = models.CharField(max_length=64, db_index=True)
    device_name = models.CharField(max_length=255)
    user_agent_summary = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="revoked_trusted_devices")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "token_hash"], name="unique_user_trusted_device_token")]
        ordering = ["-last_seen"]


class OTP(models.Model):
    PURPOSE_LOGIN = "LOGIN"
    PURPOSE_CHOICES = ((PURPOSE_LOGIN, "Login"),)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otp_challenges")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_LOGIN)
    code_digest = models.CharField(max_length=64)
    challenge_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device_token_hash = models.CharField(max_length=64, blank=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    used_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "purpose", "created_at"]), models.Index(fields=["challenge_id"])]

    @property
    def is_active(self):
        return not self.used_at and not self.invalidated_at and self.attempts < self.max_attempts and timezone.now() < self.expires_at

    @staticmethod
    def digest(code):
        key = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(key, str(code).encode("utf-8"), hashlib.sha256).hexdigest()

    def matches(self, code):
        return self.is_active and hmac.compare_digest(self.code_digest, self.digest(code))


class SupportAccessSession(models.Model):
    STATUS_CHOICES = (("PENDING", "Pending"), ("ACTIVE", "Active"), ("EXPIRED", "Expired"), ("REVOKED", "Revoked"), ("ENDED", "Ended"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="support_access_sessions")
    support_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_access_sessions")
    ticket = models.ForeignKey("support.SupportTicket", null=True, blank=True, on_delete=models.PROTECT, related_name="access_sessions")
    reason = models.TextField()
    scopes = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_support_access_sessions")
    approved_at = models.DateTimeField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["support_agent", "status", "expires_at"]), models.Index(fields=["company", "status"])]
