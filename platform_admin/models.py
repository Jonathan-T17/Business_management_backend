from django.db import models

from django.conf import settings
import uuid


class ServiceHealthEvidence(models.Model):
    """Operational evidence shared by web and worker processes; no business data."""

    service = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20)
    checked_at = models.DateTimeField()
    detail = models.CharField(max_length=400)


class SecurityIncident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    severity = models.CharField(max_length=10, choices=(("INFO", "Info"), ("WARNING", "Warning"), ("CRITICAL", "Critical")), default="WARNING")
    status = models.CharField(max_length=20, default="OPEN", choices=(("OPEN", "Open"), ("INVESTIGATING", "Investigating"), ("CONTAINED", "Contained"), ("RESOLVED", "Resolved")))
    company = models.ForeignKey("companies.Company", null=True, blank=True, on_delete=models.PROTECT)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="security_incidents")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_security_incidents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated_at", "-id")


class IncidentEvent(models.Model):
    incident = models.ForeignKey(SecurityIncident, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
