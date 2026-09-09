from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("company_setup", "0005_approvalroute"), ("reporting_schedules", "0002_reportingobligation_final_reminder_sent_and_more")]
    operations = [
        migrations.CreateModel(name="ReportingProcess", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=120)), ("description", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)), ("approval_route", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reporting_processes", to="company_setup.approvalroute")), ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reporting_processes", to="companies.company")), ("schedule", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="reporting_process", to="reporting_schedules.reportingschedule"))], options={"ordering": ["name"]}),
        migrations.AddConstraint(model_name="reportingprocess", constraint=models.UniqueConstraint(fields=("company", "name"), name="unique_company_reporting_process_name")),
    ]