from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("company_setup", "0004_request_type_definition_and_field_activity_template"), ("workflows", "0001_initial")]
    operations = [
        migrations.CreateModel(name="ApprovalRoute", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=120)), ("description", models.TextField(blank=True)), ("is_active", models.BooleanField(default=True)), ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="approval_routes", to="companies.company")), ("workflow", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="approval_route", to="workflows.workflowdefinition"))], options={"ordering": ["name"]}),
        migrations.AddConstraint(model_name="approvalroute", constraint=models.UniqueConstraint(fields=("company", "name"), name="unique_company_approval_route_name")),
    ]