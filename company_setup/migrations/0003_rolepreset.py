from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0007_delete_legacy_company_setup"),
        ("company_setup", "0002_seed_business_setup_templates"),
    ]

    operations = [
        migrations.CreateModel(
            name="RolePreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=100)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("capabilities", models.JSONField(default=list)),
                ("is_system", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="role_presets", to="companies.company")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="rolepreset",
            constraint=models.UniqueConstraint(fields=("company", "code"), name="unique_company_role_preset_code"),
        ),
    ]