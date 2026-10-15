from pathlib import Path
p=Path('forms_engine/migrations/0016_complete_form_catalogue.py');s=p.read_text(encoding='utf-8');start=s.index('def update_catalogue(');end=s.index('\nclass Migration',start)
s=s[:start]+'''def update_catalogue(apps, schema_editor):
    import json
    Starter = apps.get_model('forms_engine', 'FormStarter')
    # Older seed migrations contain replacement characters in a few examples.
    # Match only those exact stock variants; preserve operator customisations.
    def normalised(value):
        return json.dumps(value, sort_keys=True, ensure_ascii=False).replace('’', '\\ufffd').replace('—', '\\ufffd')
    for change in CHANGES:
        starter = Starter.objects.using(schema_editor.connection.alias).filter(code=change['code']).first()
        if starter and starter.name == change['old_name'] and normalised(starter.field_schema) == normalised(change['old_fields']) and normalised(starter.description) == normalised(change['old_description']):
            Starter.objects.using(schema_editor.connection.alias).filter(pk=starter.pk).update(field_schema=change['new_fields'],description=change['new_description'],name=change['new_name'])
''' + s[end:];p.write_text(s,encoding='utf-8')
p=Path('tests/security/test_form_library.py');s=p.read_text(encoding='utf-8').replace("role='EMPLOYEE')","role='EMPLOYEE', is_active=True)");p.write_text(s,encoding='utf-8')
p=Path('.notification-fix/approved-form-journey/src/components/forms/FormDesigner.tsx');s=p.read_text(encoding='utf-8').replace("Today's date — editable","Today’s date — editable");p.write_text(s,encoding='utf-8')
