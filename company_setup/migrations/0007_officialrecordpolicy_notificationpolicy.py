from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("company_setup", "0006_reportingprocess")]
    operations = [
        migrations.CreateModel(name="NotificationPolicy", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("event_code", models.CharField(max_length=80)), ("in_app_enabled", models.BooleanField(default=True)), ("email_enabled", models.BooleanField(default=False)), ("user_can_disable_email", models.BooleanField(default=True)), ("is_active", models.BooleanField(default=True)), ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_policies", to="companies.company"))]),
        migrations.CreateModel(name="OfficialRecordPolicy", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("source_type", models.CharField(max_length=50)), ("prefix", models.CharField(max_length=10)), ("automatic_issue", models.BooleanField(default=False)), ("trigger_status", models.CharField(blank=True, max_length=30)), ("is_active", models.BooleanField(default=True)), ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="official_record_policies", to="companies.company"))]),
        migrations.AddConstraint(model_name="notificationpolicy", constraint=models.UniqueConstraint(fields=("company", "event_code"), name="unique_company_notification_policy_event")),
        migrations.AddConstraint(model_name="officialrecordpolicy", constraint=models.UniqueConstraint(fields=("company", "source_type"), name="unique_company_record_policy_source")),
    ]