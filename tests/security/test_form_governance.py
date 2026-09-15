import pytest
from rest_framework.test import APIClient
from companies.models import Company
from organizations.models import UserCapabilityGrant
from forms_engine.models import FormTemplate, FormField, FormSubmission
from core.capabilities import Capabilities as C

@pytest.mark.django_db
def test_company_form_governance(django_user_model):
    company=Company.objects.create(name='Governed forms')
    builder=django_user_model.objects.create_user(email='builder@forms.test',company=company,role='EMPLOYEE')
    employee=django_user_model.objects.create_user(email='employee@forms.test',company=company,role='EMPLOYEE')
    client=APIClient();client.force_authenticate(builder)
    root='/api/v1/form-templates/'
    payload={'name':'Vehicle request','code':'vehicle','category':'REQUEST','fields':[{'key':'purpose','label':'Purpose','field_type':'TEXT','required':True}]}
    assert client.post(root,payload,format='json').status_code==403
    UserCapabilityGrant.objects.create(company=company,user=builder,capability=C.MANAGE_FORM_TEMPLATES)
    response=client.post(root,payload,format='json')
    assert response.status_code==201,response.data
    original=response.data['id'];url=root+original+'/'
    assert client.post(url+'publish/').status_code==403
    UserCapabilityGrant.objects.create(company=company,user=builder,capability=C.PUBLISH_FORM_TEMPLATES)
    assert client.post(url+'publish/').status_code==200
    client.force_authenticate(employee)
    assert client.post('/api/v1/form-submissions/',{'template':original,'data':{'purpose':'Visit'}},format='json').status_code==403
    UserCapabilityGrant.objects.create(company=company,user=employee,capability=C.SUBMIT_FORMS)
    response=client.post('/api/v1/form-submissions/',{'template':original,'data':{'purpose':'Visit'}},format='json')
    assert response.status_code==201,response.data
    submission=response.data['id']
    client.force_authenticate(builder)
    assert client.get('/api/v1/form-submissions/'+submission+'/').status_code==404
    response=client.patch(url,{'name':'Vehicle v2','fields':[{'key':'destination','label':'Destination','field_type':'TEXT'}]},format='json')
    assert response.status_code==200,response.data
    revised=response.data['id']
    assert revised!=original and response.data['version']==2
    assert FormTemplate.objects.get(pk=original).fields.get().key=='purpose'
    assert client.post(root+revised+'/publish/').status_code==200
    client.force_authenticate(employee)
    assert client.post('/api/v1/form-submissions/',{'template':original,'data':{}},format='json').status_code==400
    response=client.post('/api/v1/form-submissions/'+submission+'/submit/')
    assert response.status_code==200,response.data
    old=FormSubmission.objects.get(pk=submission)
    assert old.template_version==1 and old.schema_snapshot['fields'][0]['key']=='purpose'
    client.force_authenticate(builder)
    response=client.post(root+revised+'/copy/',{'name':'Vehicle copy','code':'vehicle-copy'})
    assert response.status_code==201,response.data
    assert response.data['version']==1 and response.data['workflow'] is None
    assert client.get(root+'starters/').status_code==200
    builder.role='SUPERUSER';builder.save()
    assert client.get(url).status_code==403

@pytest.mark.django_db
def test_sensitive_configuration_does_not_grant_data(django_user_model):
    company=Company.objects.create(name='Sensitive form tenant')
    actor=django_user_model.objects.create_user(email='sensitive@forms.test',company=company,role='EMPLOYEE')
    for cap in (C.MANAGE_FORM_TEMPLATES,C.PUBLISH_FORM_TEMPLATES,C.SUBMIT_FORMS):
        UserCapabilityGrant.objects.create(company=company,user=actor,capability=cap)
    client=APIClient();client.force_authenticate(actor)
    payload={'name':'HR','code':'hr','fields':[{'key':'salary','label':'Salary','field_type':'DECIMAL','classification':'COMPENSATION'}]}
    assert client.post('/api/v1/form-templates/',payload,format='json').status_code==403
    UserCapabilityGrant.objects.create(company=company,user=actor,capability=C.CONFIGURE_SENSITIVE_FORMS)
    response=client.post('/api/v1/form-templates/',payload,format='json')
    assert response.status_code==201,response.data
    pk=response.data['id'];assert client.post(f'/api/v1/form-templates/{pk}/publish/').status_code==200
    response=client.post('/api/v1/form-submissions/',{'template':pk,'data':{'salary':'500'}},format='json')
    assert response.status_code==201,response.data
    assert response.data['data']['salary']=='[REDACTED]'
    submission_id = response.data['id']
    response = client.patch(f'/api/v1/form-submissions/{submission_id}/', {'data': {'salary': '[REDACTED]'}}, format='json')
    assert response.status_code == 200, response.data
    assert FormSubmission.objects.get(pk=submission_id).data['salary'] == '500'

@pytest.mark.django_db
def test_hidden_required_question_does_not_block_submission(django_user_model):
    company = Company.objects.create(name='Conditional forms')
    actor = django_user_model.objects.create_user(email='conditional@forms.test', company=company, role='ADMIN')
    client = APIClient(); client.force_authenticate(actor)
    response = client.post('/api/v1/form-templates/', {
        'name': 'Travel', 'code': 'conditional-travel', 'fields': [
            {'key': 'overnight', 'label': 'Overnight?', 'field_type': 'BOOLEAN', 'order': 0},
            {'key': 'hotel', 'label': 'Hotel', 'field_type': 'TEXT', 'required': True, 'order': 1,
             'validation_rules': {'show_when': {'field': 'overnight', 'equals': True}}},
        ],
    }, format='json')
    assert response.status_code == 201, response.data
    template_id = response.data['id']
    assert client.post(f'/api/v1/form-templates/{template_id}/publish/').status_code == 200
    for overnight, expected in ((False, 200), (True, 400)):
        response = client.post('/api/v1/form-submissions/', {'template': template_id, 'data': {'overnight': overnight}}, format='json')
        assert response.status_code == 201, response.data
        response = client.post(f"/api/v1/form-submissions/{response.data['id']}/submit/")
        assert response.status_code == expected, response.data
