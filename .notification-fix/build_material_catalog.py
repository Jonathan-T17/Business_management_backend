from pathlib import Path
import sys, importlib
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
path=Path('forms_engine/starters.py')
text=path.read_text()
start=text.index('for material_design in STARTERS:')
end=text.index('\n\ndef question',start)
block=text[start:end]
text=text[:start]+text[end:]+'\n\n'+block+'\n'
path.write_text(text)
from forms_engine.starters import STARTERS
old=importlib.import_module('forms_engine.migrations.0008_common_form_library').DESIGNS
codes={'material-request','material-dispatch','material-receipt','material-return'}
pairs=[(next(d for d in old if d['code']==design['code'])['fields'],design) for design in STARTERS if design['code'] in codes]
source='''from django.db import migrations

DESIGNS = %s

def upgrade(apps, schema_editor):
    Starter=apps.get_model('forms_engine','FormStarter')
    for original, design in DESIGNS:
        starter=Starter.objects.using(schema_editor.connection.alias).filter(code=design['code']).first()
        if starter and starter.field_schema == original:
            starter.field_schema=design['fields']
            starter.save(update_fields=['field_schema'])

class Migration(migrations.Migration):
    dependencies=[('forms_engine','0011_material_item_lists')]
    operations=[migrations.RunPython(upgrade,migrations.RunPython.noop)]
'''
Path('forms_engine/migrations/0012_connected_material_catalog.py').write_text(source % repr(pairs),encoding='utf-8')
