from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0005_company_setup_and_locale_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="date_format",
            field=models.CharField(default="DD/MM/YYYY", max_length=20),
        ),
        migrations.AddField(
            model_name="company",
            name="setup_completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="company",
            name="week_starts_on",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]