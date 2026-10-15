from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0019_return_archived_selections')]
    operations = [
        migrations.AddField(model_name='formsubmission', name='client_request_id', field=models.UUIDField(blank=True, editable=False, null=True)),
        migrations.AddConstraint(model_name='formsubmission', constraint=models.UniqueConstraint(fields=('company', 'submitted_by', 'client_request_id'), name='unique_form_draft_request')),
    ]
