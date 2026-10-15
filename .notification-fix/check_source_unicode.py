from importlib import import_module
from forms_engine.starters import STARTERS
m=import_module('forms_engine.migrations.0014_plain_language_form_library')
for code in ['daily-report','collection-record','vehicle-request']:
 t=next(x for x in STARTERS if x['code']==code);old=next(x for x in m.CHANGES if x['code']==code)
 print(code,'runtime',ascii(t['description']),ascii(t['fields'][0]['label']), 'migration14',ascii(old['new_description']))
