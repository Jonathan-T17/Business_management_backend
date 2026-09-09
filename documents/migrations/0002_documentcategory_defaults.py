from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="documentcategory",
            name="default_visibility",
            field=models.CharField(
                choices=[("COMPANY", "Company"), ("BRANCH", "Branch"), ("DEPARTMENT", "Department"), ("TEAM", "Team"), ("MANAGEMENT", "Management")],
                default="COMPANY",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="documentcategory",
            name="sensitive",
            field=models.BooleanField(default=False),
        ),
    ]