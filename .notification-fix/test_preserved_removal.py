from pathlib import Path
p=Path('tests/security/test_ready_form_journey.py');s=p.read_text(encoding='utf-8');s=s.replace("for field in Versions.field_data(template)]+", "for field in Versions.field_data(template) if field['key']!='company_name']+")
s=s.replace("assert revision.fields.filter(key='source_reference').exists()", "assert revision.fields.filter(key='source_reference').exists()\n    assert not revision.fields.filter(key='company_name').exists()")
p.write_text(s,encoding='utf-8')
