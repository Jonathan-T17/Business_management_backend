import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_notificationpreference_emaildeliverylog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="companies.company",
            ),
        ),
    ]