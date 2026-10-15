from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0008_common_form_library')]
    operations = [migrations.AddField(model_name='formtemplate', name='audience_position_ids', field=models.JSONField(default=list, blank=True))]
