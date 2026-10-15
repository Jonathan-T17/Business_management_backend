from pathlib import Path
p=Path('tests/security/test_ready_form_journey.py');s=p.read_text(encoding='utf-8');s+='''

@pytest.mark.django_db
@pytest.mark.parametrize('source', [['TODAY'], {'type':'TODAY'}, 'UNKNOWN'])
def test_invalid_automatic_sources_are_rejected_without_server_errors(journey,source):
    client,admin,employee,peer,stranger,template=journey
    client.force_authenticate(admin)
    response=client.post('/api/v1/form-templates/',{'name':'Invalid defaults','code':'invalid-defaults','fields':[{'key':'date','label':'Date','field_type':'DATE','validation_rules':{'default_source':source}}]},format='json')
    assert response.status_code==400,response.data
    assert not FormTemplate.objects.filter(code='invalid-defaults').exists()
''';p.write_text(s,encoding='utf-8')
