from importlib import import_module
import json
from django.db import migrations


def repair_stock(apps, schema_editor):
    changes = import_module('forms_engine.migrations.0016_complete_form_catalogue').CHANGES
    Starter = apps.get_model('forms_engine', 'FormStarter')
    def normalised(value):
        text = json.dumps(value, sort_keys=True, ensure_ascii=False)
        for char in '’‘“”—–…':
            text = text.replace(char.encode('utf-8').decode('cp1252', errors='replace'), char)
        return text.replace('’', '\ufffd').replace('—', '\ufffd')
    for change in changes:
        starter = Starter.objects.using(schema_editor.connection.alias).filter(code=change['code']).first()
        if not starter:
            continue
        current = {'name': starter.name, 'description': starter.description, 'fields': starter.field_schema}
        variants = [{key: change[prefix + key] for key in ('name', 'description', 'fields')} for prefix in ('old_', 'new_')]
        if any(normalised(current) == normalised(variant) for variant in variants):
            Starter.objects.using(schema_editor.connection.alias).filter(pk=starter.pk).update(name=change['new_name'],description=change['new_description'],field_schema=change['new_fields'])


class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0016_complete_form_catalogue')]
    operations = [migrations.RunPython(repair_stock, migrations.RunPython.noop)]
