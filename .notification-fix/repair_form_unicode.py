from pathlib import Path
p=Path('forms_engine/starters.py');s=p.read_text(encoding='utf-8')
for char in '’‘“”—–…':
 s=s.replace(char.encode('utf-8').decode('cp1252',errors='replace'),char)
p.write_text(s,encoding='utf-8')
p=Path('forms_engine/migrations/0016_complete_form_catalogue.py');s=p.read_text(encoding='utf-8')
for char in '’‘“”—–…': s=s.replace(char.encode('utf-8').decode('cp1252',errors='replace'),char)
p.write_text(s,encoding='utf-8')
p=Path('tests/security/test_ready_form_journey.py');s=p.read_text(encoding='utf-8');s=s.replace("assert client.get(f'/api/v1/form-templates/{template.pk}/?builder=1').status_code==403","assert client.get(f'/api/v1/form-templates/{template.pk}/?mode=builder').status_code==200\n    assert client.patch(f'/api/v1/form-templates/{template.pk}/',{'name':'Forbidden change'},format='json').status_code==403")
p.write_text(s,encoding='utf-8')
