from importlib import import_module
from forms_engine.models import FormStarter
from forms_engine.starters import STARTERS
changes=import_module('forms_engine.migrations.0016_complete_form_catalogue').CHANGES
for change in changes:
 s=FormStarter.objects.get(code=change['code'])
 print(s.code,'name',s.name, 'expected',change['old_name'],'fields',s.field_schema==change['old_fields'],'description',s.description==change['old_description'])
