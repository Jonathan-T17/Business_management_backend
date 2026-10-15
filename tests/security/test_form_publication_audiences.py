import pytest
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from companies.models import Company, Branch
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities as C
from forms_engine.models import FormTemplate


@pytest.mark.django_db
def test_location_publication_sharing_and_deletion(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: True)
    company = Company.objects.create(name='Publication company')
    headquarters = Branch.objects.create(company=company, name='Head office')
    branch = Branch.objects.create(company=company, name='Branch')
    other_branch = Branch.objects.create(company=company, name='Other branch')
    company.headquarters = headquarters; company.save()
    foreign = Company.objects.create(name='Other tenant')
    foreign_branch = Branch.objects.create(company=foreign, name='Foreign')
    admin = django_user_model.objects.create_user(email='publisher@test.local', company=company, role='ADMIN', is_active=True)
    workers = [django_user_model.objects.create_user(email=f'publication-{index}@test.local', company=company, branch=location, role='EMPLOYEE', is_active=True) for index, location in enumerate([headquarters, branch, other_branch])]
    for worker in workers:
        UserCapabilityGrant.objects.create(company=company, user=worker, capability=C.SUBMIT_FORMS)
    client = APIClient(); client.force_authenticate(admin)
    root = '/api/v1/form-templates/'
    def create(code):
        response = client.post(root, {'code':code, 'name':code, 'fields':[{'key':'note','label':'Note','field_type':'TEXT'}]}, format='json')
        assert response.status_code == 201, response.data
        return response.data['id']
    tid = create('branch-publication')
    assert client.post(f'{root}{tid}/publish/', {'audience':'BRANCHES', 'branch_ids':[foreign_branch.pk]}, format='json').status_code == 400
    response = client.post(f'{root}{tid}/publish/', {'audience':'BRANCHES', 'branch_ids':[branch.pk], 'entry_visibility':'AUDIENCE'}, format='json')
    assert response.status_code == 200, response.data
    for index, worker in enumerate(workers):
        client.force_authenticate(worker)
        assert client.get(f'{root}{tid}/').status_code == (200 if index == 1 else 404)
    client.force_authenticate(workers[1])
    response = client.post('/api/v1/form-submissions/', {'template':tid,'data':{'note':'Branch work'}}, format='json')
    assert response.status_code == 201, response.data
    sid = response.data['id']
    peer = django_user_model.objects.create_user(email='publication-peer@test.local',company=company,branch=branch,role='EMPLOYEE',is_active=True)
    UserCapabilityGrant.objects.create(company=company,user=peer,capability=C.SUBMIT_FORMS)
    client.force_authenticate(peer)
    assert client.get(f'/api/v1/form-submissions/{sid}/').status_code == 404
    client.force_authenticate(workers[1]); assert client.post(f'/api/v1/form-submissions/{sid}/submit/').status_code == 200
    client.force_authenticate(peer); assert client.get(f'/api/v1/form-submissions/{sid}/').status_code == 200
    client.force_authenticate(workers[2]); assert client.get(f'/api/v1/form-submissions/{sid}/').status_code == 404
    client.force_authenticate(admin); assert client.delete(f'{root}{tid}/').status_code == 204
    assert client.get(f'{root}{tid}/?mode=builder').status_code == 404
    client.force_authenticate(workers[1]); assert client.get(f'/api/v1/form-submissions/{sid}/').status_code == 200
    client.force_authenticate(admin)
    for scope, allowed in [('COMPANY', [0,1,2]), ('HEADQUARTERS', [0])]:
        current = create(scope.lower())
        assert client.post(f'{root}{current}/publish/', {'audience':scope}, format='json').status_code == 200
        for index, worker in enumerate(workers):
            client.force_authenticate(worker)
            assert client.get(f'{root}{current}/').status_code == (200 if index in allowed else 404)
        client.force_authenticate(admin)
    response = client.post(f'{root}select-starters/', {'codes':['daily-report']}, format='json'); assert response.status_code == 201
    selected = response.data['created'][0]['id']; assert client.delete(f'{root}{selected}/').status_code == 204
    response = client.post(f'{root}select-starters/', {'codes':['daily-report']}, format='json'); assert response.status_code == 201, response.data
    assert response.data['created'][0]['id'] != selected
    assert FormTemplate.objects.get(pk=selected).workspace_deleted


@pytest.mark.django_db
def test_confidential_publication_requires_authority_confirmation_and_stays_in_tenant(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: True)
    company = Company.objects.create(name='Confidential audience')
    admin = django_user_model.objects.create_user(email='confidential-publisher@test.local',company=company,role='ADMIN',is_active=True)
    worker = django_user_model.objects.create_user(email='confidential-worker@test.local',company=company,role='EMPLOYEE',is_active=True)
    UserCapabilityGrant.objects.create(company=company,user=worker,capability=C.SUBMIT_FORMS)
    client=APIClient();client.force_authenticate(admin)
    root='/api/v1/form-templates/'
    response=client.post(root,{'name':'Protected','code':'protected-audience','fields':[{'key':'note','label':'Note','field_type':'TEXT'}]},format='json'); assert response.status_code==201
    tid=response.data['id']
    payload={'audience':'COMPANY','entry_visibility':'AUDIENCE','share_confidential':True,'confirm_confidential_access':True}
    assert client.post(f'{root}{tid}/publish/',payload,format='json').status_code==403
    UserCapabilityGrant.objects.create(company=company,user=admin,capability=C.CONFIGURE_SENSITIVE_FORMS)
    # Reload actor so cached capabilities cannot mask the grant change.
    admin=django_user_model.objects.get(pk=admin.pk);client.force_authenticate(admin)
    payload['confirm_confidential_access']=False
    assert client.post(f'{root}{tid}/publish/',payload,format='json').status_code==403
    template=FormTemplate.objects.get(pk=tid); template.fields.update(classification='COMPENSATION')
    payload['confirm_confidential_access']=True
    response=client.post(f'{root}{tid}/publish/',payload,format='json'); assert response.status_code==200,response.data
    client.force_authenticate(worker)
    response=client.post('/api/v1/form-submissions/',{'template':tid,'data':{'note':'Shared explicitly'}},format='json');assert response.status_code==201,response.data
    sid=response.data['id']
    files=f'/api/v1/form-submissions/{sid}/attachments/'
    response=client.post(files, {'file':SimpleUploadedFile('shared.txt',b'Authorized evidence')})
    assert response.status_code==201,response.data
    file_id=response.data['id']
    assert client.post(f'/api/v1/form-submissions/{sid}/submit/').status_code==200
    assert client.get(f'/api/v1/form-submissions/{sid}/').data['data']['note']=='Shared explicitly'
    peer=django_user_model.objects.create_user(email='confidential-peer@test.local',company=company,role='EMPLOYEE',is_active=True)
    UserCapabilityGrant.objects.create(company=company,user=peer,capability=C.SUBMIT_FORMS)
    client.force_authenticate(peer)
    assert client.get(f'/api/v1/form-submissions/{sid}/').data['data']['note']=='Shared explicitly'
    response=client.get(f'{files}{file_id}/');assert response.status_code==200
    assert b''.join(response.streaming_content)==b'Authorized evidence'
    outsider_company=Company.objects.create(name='Outside confidential')
    outsider=django_user_model.objects.create_user(email='confidential-outsider@test.local',company=outsider_company,role='ADMIN',is_active=True)
    client.force_authenticate(outsider);assert client.get(f'/api/v1/form-submissions/{sid}/').status_code==404
    assert client.get(f'{files}{file_id}/').status_code==404
