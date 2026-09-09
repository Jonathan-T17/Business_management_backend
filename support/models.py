import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class SupportTicket(models.Model):
    CATEGORY_CHOICES = tuple((x, x.replace("_", " ").title()) for x in (
        "ACCOUNT","SECURITY","SUBSCRIPTION","BILLING","REPORTING","WORKFLOW","EMPLOYEES","DOCUMENTS","FIELD_OPERATIONS","TECHNICAL","FEATURE_REQUEST","OTHER"))
    PRIORITY_CHOICES = (("LOW","Low"),("NORMAL","Normal"),("HIGH","High"),("URGENT","Urgent"))
    STATUS_CHOICES = (("OPEN","Open"),("IN_PROGRESS","In progress"),("WAITING_FOR_CUSTOMER","Waiting for customer"),("RESOLVED","Resolved"),("CLOSED","Closed"))
    SENSITIVITY_CHOICES = (("NORMAL","Normal"),("RESTRICTED","Restricted"),("SECURITY","Security"),("BILLING","Billing"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=32, unique=True, editable=False)
    company = models.ForeignKey("companies.Company", on_delete=models.PROTECT, related_name="support_tickets")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_tickets")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="OTHER")
    sensitivity = models.CharField(max_length=20, choices=SENSITIVITY_CHOICES, default="NORMAL", db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    requested_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="OPEN", db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_support_tickets")
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("company","status","-created_at")), models.Index(fields=("sensitivity","status"))]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"SUP-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
        return super().save(*args, **kwargs)

class SupportMessage(models.Model):
    VISIBILITY_CHOICES = (("CUSTOMER","Customer visible"),("INTERNAL","Internal support note"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_messages")
    body = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="CUSTOMER")
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ("created_at",)
