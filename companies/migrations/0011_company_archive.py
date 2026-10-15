from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("companies", "0010_company_headquarters"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="company", name="archived_at", field=models.DateTimeField(blank=True, null=True, db_index=True)),
        migrations.AddField(model_name="company", name="recovery_until", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="company", name="archived_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workspaces_archived", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="company", name="archive_reason", field=models.TextField(blank=True)),
        migrations.AddField(model_name="company", name="active_before_archive", field=models.BooleanField(default=True)),
        migrations.AddConstraint(model_name="company", constraint=models.CheckConstraint(condition=models.Q(archived_at__isnull=True) | models.Q(is_active=False), name="archived_company_is_inactive")),
    ]
