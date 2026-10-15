import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0011_company_archive")]
    operations = [
        migrations.AddField(model_name="company", name="deletion_hold_reason", field=models.TextField(blank=True)),
        migrations.CreateModel(name="WorkspacePurgeReceipt", fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("workspace_id", models.PositiveBigIntegerField(unique=True)),
            ("status", models.CharField(max_length=24, default="FILES_PENDING", choices=[("FILES_PENDING", "File cleanup pending"), ("COMPLETE", "Live data removed"), ("BACKUP_BLOCKED", "Restored backup blocked")])),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("completed_at", models.DateTimeField(null=True, blank=True)),
            ("counts", models.JSONField(default=dict)),
            ("pending_files", models.JSONField(default=list)),
            ("failure_code", models.CharField(max_length=80, blank=True)),
        ], options={"ordering": ("-created_at",)}),
    ]
