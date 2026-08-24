from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    STATUS_CHOICES = (("SUCCESS", "Success"), ("FAILED", "Failed"))
    ACTION_CHOICES = (
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("ACCESS", "Access"),
        ("SECURITY", "Security"),
    )
    SEVERITY_CHOICES = (
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("CRITICAL", "Critical"),
    )
    ACTOR_CHOICES = (
        ("USER", "User"),
        ("SYSTEM", "System"),
        ("API", "API"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="audit_logs")
    company = models.ForeignKey("companies.Company", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="audit_logs")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="audit_logs")

    action = models.CharField(max_length=120, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="INFO")
    actor_type = models.CharField(max_length=20, choices=ACTOR_CHOICES, default="USER")

    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUCCESS")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "branch", "action", "severity"])]

    def __str__(self):
        return f"{self.action} ({self.status})"


class LoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="login_history")
    company = models.ForeignKey("companies.Company", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="login_history")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="login_history")
    session = models.ForeignKey("security.ActiveSession", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="login_history")

    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    browser = models.CharField(max_length=255)
    operating_system = models.CharField(max_length=255)
    device = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)

    successful = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ActiveSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="active_sessions")
    company = models.ForeignKey("companies.Company", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="active_sessions")
    branch = models.ForeignKey("companies.Branch", null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="active_sessions")

    refresh_token_jti = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    browser = models.CharField(max_length=255)
    operating_system = models.CharField(max_length=255)
    device = models.CharField(max_length=255)

    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-last_activity"]
        indexes = [models.Index(fields=["user", "is_active"])]


class FailedLoginAttempt(models.Model):
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    company = models.ForeignKey("companies.Company", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="failed_login_attempts")

    attempts = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    locked_by_system = models.BooleanField(default=True)
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("email", "ip_address")
        indexes = [models.Index(fields=["email", "ip_address"])]





class TrustedDevice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trusted_devices",
    )

    fingerprint = models.CharField(
        max_length=255,
        db_index=True,  # faster lookups
    )

    device_name = models.CharField(
        max_length=255,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    last_seen = models.DateTimeField(
        auto_now=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Mark inactive if device should no longer be trusted",
    )

    class Meta:
        unique_together = ("user", "fingerprint")
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.device_name} ({self.user.email})"






class OTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    fingerprint = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "fingerprint", "code"])]
