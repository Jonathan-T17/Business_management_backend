import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reference", models.CharField(editable=False, max_length=24, unique=True)),
                ("category", models.CharField(choices=[("ACCOUNT", "Account"), ("SECURITY", "Security"), ("SUBSCRIPTION", "Subscription"), ("BILLING", "Billing"), ("REPORTING", "Reporting"), ("WORKFLOW", "Workflow"), ("EMPLOYEES", "Employees"), ("DOCUMENTS", "Documents"), ("FIELD_OPERATIONS", "Field Operations"), ("TECHNICAL", "Technical"), ("FEATURE_REQUEST", "Feature Request"), ("OTHER", "Other")], default="OTHER", max_length=30)),
                ("subject", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("priority", models.CharField(choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High"), ("URGENT", "Urgent")], default="NORMAL", max_length=10)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("IN_PROGRESS", "In progress"), ("WAITING_FOR_CUSTOMER", "Waiting for customer"), ("RESOLVED", "Resolved"), ("CLOSED", "Closed")], default="OPEN", max_length=24)),
                ("context", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_support_tickets", to=settings.AUTH_USER_MODEL)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_tickets", to="companies.company")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="support_tickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-created_at",), "indexes": [models.Index(fields=("company", "status", "-created_at"), name="support_sup_company_159a5b_idx")]},
        ),
        migrations.CreateModel(
            name="SupportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="support_messages", to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="support.supportticket")),
            ],
            options={"ordering": ("created_at",)},
        ),
    ]
