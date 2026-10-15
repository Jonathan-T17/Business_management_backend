from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forms_engine.starters import STARTERS

source = '''from django.db import migrations

DESIGNS = %s

def seed(apps, schema_editor):
    Starter = apps.get_model('forms_engine', 'FormStarter')
    for design in DESIGNS:
        Starter.objects.using(schema_editor.connection.alias).get_or_create(
            code=design['code'], defaults={
                'name': design['name'], 'category': design['category'],
                'description': design.get('description', ''), 'field_schema': design['fields']})

class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0007_collection_form_starter')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
'''
Path('forms_engine/migrations/0008_common_form_library.py').write_text(source % repr(STARTERS), encoding='utf-8')
