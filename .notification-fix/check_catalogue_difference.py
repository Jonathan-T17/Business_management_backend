from importlib import import_module
from forms_engine.models import FormStarter
changes=import_module('forms_engine.migrations.0016_complete_form_catalogue').CHANGES
for change in changes:
 s=FormStarter.objects.get(code=change['code'])
 if s.description!=change['old_description']: print(s.code,repr(s.description),repr(change['old_description']))
 for old,current in zip(change['old_fields'],s.field_schema):
  if old!=current: print(s.code,old,current);break
