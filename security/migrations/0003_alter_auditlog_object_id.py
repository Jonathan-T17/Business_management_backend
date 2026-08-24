from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("security", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="object_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
            ),
        ),
    ]
