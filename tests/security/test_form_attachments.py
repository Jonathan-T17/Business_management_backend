import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from companies.models import Company
from core.capabilities import Capabilities as C
from organizations.models import UserCapabilityGrant
from forms_engine.models import FormSubmission

@pytest.mark.django_db
def test_person_audience_and_attachment_boundaries(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: True)
    company = Company.objects.create(name='Attachment tenant')
    owner = django_user_model.objects.create_user(email='file-owner@test.local', company=company, role='ADMIN',is_active=True)
    other = django_user_model.objects.create_user(email='file-other@test.local', company=company, role='EMPLOYEE',is_active=True)
    UserCapabilityGrant.objects.create(company=company, user=other, capability=C.SUBMIT_FORMS)
    client = APIClient(); client.force_authenticate(owner)
    root = '/api/v1/form-templates/'
    payload = {'name':'Evidence', 'code':'evidence', 'audience_user_ids':[str(owner.pk)], 'fields':[{'key':'note','label':'Note','field_type':'TEXT'}]}
    response = client.post(root, payload, format='json'); assert response.status_code == 201, response.data
    template_id = response.data['id']
    assert client.post(f'{root}{template_id}/publish/').status_code == 200
    client.force_authenticate(other)
    assert client.post('/api/v1/form-submissions/', {'template':template_id,'data':{}}, format='json').status_code == 400
    client.force_authenticate(owner)
    response = client.post('/api/v1/form-submissions/', {'template':template_id,'data':{}}, format='json')
    assert response.status_code == 201, response.data
    sid = response.data['id']; url = f'/api/v1/form-submissions/{sid}/attachments/'
    assert client.post(url, {'file':SimpleUploadedFile('bad.exe', b'bad')}).status_code == 400
    response = client.post(url, {'file':SimpleUploadedFile('evidence.txt', b'private evidence')})
    assert response.status_code == 201, response.data
    fid = response.data['id']; download = f'{url}{fid}/'
    response = client.get(download); assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'private evidence'
    client.force_authenticate(other)
    assert client.get(download).status_code == 404
    client.force_authenticate(owner)
    assert client.delete(download).status_code == 204
    assert client.get(download).status_code == 404
    response = client.post(url, {'file':SimpleUploadedFile('retained.txt', b'evidence')}); assert response.status_code == 201
    fid = response.data['id']
    assert client.post(f'/api/v1/form-submissions/{sid}/submit/').status_code == 200
    assert client.post(url, {'file':SimpleUploadedFile('late.txt', b'late')}).status_code == 403
    assert client.delete(f'{url}{fid}/').status_code == 403
    assert client.delete(f'/api/v1/attachments/{fid}/').status_code == 400
    foreign = Company.objects.create(name='Foreign')
    outsider = django_user_model.objects.create_user(email='outsider@test.local', company=foreign, role='EMPLOYEE',is_active=True)
    payload['code']='invalid'; payload['audience_user_ids']=[str(outsider.pk)]
    assert client.post(root, payload, format='json').status_code == 400
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: False)
    fresh=client.post('/api/v1/form-submissions/', {'template':template_id,'data':{}}, format='json')
    assert fresh.status_code==201
    assert client.post(f"/api/v1/form-submissions/{fresh.data['id']}/attachments/", {'file':SimpleUploadedFile('quota.txt', b'blocked')}).status_code==400
    owner.role='SUPERUSER';owner.save()
    assert client.get(url).status_code == 403

@pytest.mark.django_db
def test_restricted_form_files_are_not_exposed(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: True)
    company=Company.objects.create(name='Restricted files')
    actor=django_user_model.objects.create_user(email='restricted-files@test.local',company=company,role='ADMIN',is_active=True)
    UserCapabilityGrant.objects.create(company=company,user=actor,capability=C.CONFIGURE_SENSITIVE_FORMS)
    client=APIClient();client.force_authenticate(actor)
    response=client.post('/api/v1/form-templates/',{'name':'Pay','code':'pay-files','fields':[{'key':'salary','label':'Salary','field_type':'DECIMAL','classification':'COMPENSATION'}]},format='json')
    assert response.status_code==201,response.data
    tid=response.data['id'];assert client.post(f'/api/v1/form-templates/{tid}/publish/').status_code==200
    response=client.post('/api/v1/form-submissions/',{'template':tid,'data':{'salary':'100'}},format='json')
    assert response.status_code==201,response.data
    sid=response.data['id'];url=f'/api/v1/form-submissions/{sid}/attachments/'
    response=client.post(url,{'file':SimpleUploadedFile('salary.txt',b'100')});assert response.status_code==201,response.data
    fid=response.data['id']
    assert client.get(url).data['files']==[]
    assert client.get(f'{url}{fid}/').status_code==403
    assert client.get(f'/api/v1/attachments/{fid}/download/').status_code==404
