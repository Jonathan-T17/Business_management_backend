from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [
        migrations.AddField(model_name="plan", name="advanced_workflows_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="plan", name="custom_forms_enabled", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="plan", name="field_operations_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="plan", name="max_branches", field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="plan", name="official_records_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="plan", name="storage_limit_bytes", field=models.PositiveBigIntegerField(default=1073741824)),
    ]