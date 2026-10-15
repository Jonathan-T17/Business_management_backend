from importlib import import_module
from forms_engine.models import FormStarter
from forms_engine.starters import STARTERS
m=import_module('forms_engine.migrations.0016_complete_form_catalogue')
for code in ['daily-report','collection-record','payment-collection']:
 s=FormStarter.objects.get(code=code);c=next(x for x in m.CHANGES if x['code']==code);live=next(x for x in STARTERS if x['code']==code)
 print(code,s.name,len(s.field_schema),len(live['fields']),s.field_schema==live['fields'])
 if code=='daily-report':print(ascii(s.description),ascii(c['old_description']),ascii(c['new_description']))
