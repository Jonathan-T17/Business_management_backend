import uuid
from django.conf import settings
from django.db import models


class WorkspacePurgeReceipt(models.Model):
    """Minimal deletion ledger; file manifest exists only until cleanup finishes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.PositiveBigIntegerField(unique=True)
    status = models.CharField(max_length=24, default="FILES_PENDING", choices=(
        ("FILES_PENDING", "File cleanup pending"), ("COMPLETE", "Live data removed"),
        ("BACKUP_BLOCKED", "Restored backup blocked")))
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    counts = models.JSONField(default=dict)
    pending_files = models.JSONField(default=list)
    failure_code = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ("-created_at",)
