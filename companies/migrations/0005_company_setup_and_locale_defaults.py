from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0004_company_official_name_company_registration_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="country",
            field=models.CharField(blank=True, max_length=2),
        ),
        migrations.AddField(
            model_name="company",
            name="default_currency",
            field=models.CharField(default="RWF", max_length=3),
        ),
        migrations.AddField(
            model_name="company",
            name="timezone",
            field=models.CharField(default="UTC", max_length=100),
        ),
        migrations.CreateModel(
            name="CompanySetup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completed_steps", models.JSONField(blank=True, default=list)),
                ("skipped_steps", models.JSONField(blank=True, default=list)),
                ("is_completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="setup", to="companies.company")),
            ],
            options={
                "verbose_name": "company setup",
                "verbose_name_plural": "company setups",
            },
        ),
    ]