from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("forms_engine", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="formtemplate",
            name="lifecycle_status",
            field=models.CharField(
                choices=[("DRAFT", "Draft"), ("PUBLISHED", "Published"), ("ARCHIVED", "Archived")],
                default="DRAFT",
                max_length=20,
            ),
        ),
    ]