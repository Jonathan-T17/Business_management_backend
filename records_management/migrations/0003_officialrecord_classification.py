from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('records_management', '0002_officialrecord_void_reason_officialrecord_voided_at_and_more')]
    operations = [
        # Historical records have no trustworthy stored classification.
        # Keep them restricted until deliberately reviewed; new issuance supplies its classification.
        migrations.AddField(
            model_name='officialrecord', name='classification',
            field=models.CharField(max_length=30, default='SECURITY_SENSITIVE'),
        ),
        migrations.AlterField(
            model_name='officialrecord', name='classification',
            field=models.CharField(max_length=30, default='NORMAL'),
        ),
    ]
