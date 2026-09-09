from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0006_company_business_configuration"),
    ]

    operations = [
        migrations.DeleteModel(name="CompanySetup"),
    ]