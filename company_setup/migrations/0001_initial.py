from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("companies", "0007_delete_legacy_company_setup"),
    ]

    operations = [
        migrations.CreateModel(
            name="BusinessSetupTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("configuration", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CompanySetupState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_step", models.CharField(blank=True, max_length=50)),
                ("skipped_steps", models.JSONField(blank=True, default=list)),
                ("completed_steps", models.JSONField(blank=True, default=list)),
                ("selected_template", models.CharField(blank=True, max_length=50)),
                ("onboarding_completed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="setup_state", to="companies.company")),
            ],
        ),
    ]