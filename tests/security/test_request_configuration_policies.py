from datetime import date
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from companies.models import Company
from company_setup.models import RequestTypeDefinition
from workflows.models import WorkflowDefinition
from requests_app.models import BusinessRequest
from requests_app.services import BusinessRequestLifecycleService
from subscriptions.services import SubscriptionService

@pytest.fixture
def request_policy_workspace(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.ATTACHMENT_SCAN_REQUIRED = False
    settings.ATTACHMENT_SCANNER = ''
    monkeypatch.setattr(SubscriptionService, 'can_upload', lambda company, additional_bytes=0: True)
    home = Company.objects.create(name='Request policy home')
    foreign = Company.objects.create(name='Request policy foreign')
    admin = django_user_model.objects.create_user(email='policy-admin@example.test', company=home, role='ADMIN', is_active=True)
    owner = django_user_model.objects.create_user(email='policy-owner@example.test', company=home, role='EMPLOYEE', is_active=True)
    peer = django_user_model.objects.create_user(email='policy-peer@example.test', company=home, role='EMPLOYEE', is_active=True)
    outsider = django_user_model.objects.create_user(email='policy-foreign@example.test', company=foreign, role='ADMIN', is_active=True)
    route = WorkflowDefinition.objects.create(company=home, name='Request policy approval', code='policy-route', target_type='REQUEST')
    client = APIClient(); client.force_authenticate(admin)
    return home, foreign, admin, owner, peer, outsider, route, client

@pytest.mark.django_db
@pytest.mark.parametrize('enabled,required',[('amount_enabled','amount_required'),('quantity_enabled','quantity_required'),('needed_by_enabled','needed_by_required'),('attachments_allowed','attachments_required')])
def test_request_settings_reject_disabled_required_policy(request_policy_workspace, enabled, required):
    *_, client = request_policy_workspace
    response = client.post('/api/v1/company-setup/request-types/', {'code':enabled,'name':enabled,enabled:False,required:True}, format='json')
    assert response.status_code == 400, response.data

@pytest.mark.django_db
def test_request_configuration_full_policies_and_route_boundaries(request_policy_workspace):
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    wrong = WorkflowDefinition.objects.create(company=home, name='Report only route', code='report-only', target_type='REPORT')
    inactive = WorkflowDefinition.objects.create(company=home, name='Inactive route', code='inactive', target_type='REQUEST', is_active=False)
    other = WorkflowDefinition.objects.create(company=foreign, name='Foreign route', code='foreign', target_type='REQUEST')
    payload = {'code':'supplies','name':'Supplies','description':'Explain the need','sensitive':True,'amount_enabled':True,'amount_required':True,'quantity_enabled':True,'quantity_required':True,'needed_by_enabled':True,'needed_by_required':True,'attachments_allowed':True,'attachments_required':True,'workflow':route.pk}
    response = client.post('/api/v1/company-setup/request-types/', payload, format='json')
    assert response.status_code == 201, response.data
    definition = RequestTypeDefinition.objects.get(pk=response.data['id'])
    duplicate = client.post('/api/v1/company-setup/request-types/', {**payload, 'code':'SUPPLIES'}, format='json')
    assert duplicate.status_code == 400, duplicate.data
    for bad in (wrong,inactive,other):
        assert client.patch(f'/api/v1/company-setup/request-types/{definition.pk}/', {'workflow':bad.pk}, format='json').status_code == 400
    choices = client.get('/api/v1/company-setup/request-types/approval-choices/')
    assert choices.status_code == 200 and choices.data == [{'id':route.pk,'name':route.name}]
    RequestTypeDefinition.objects.create(company=foreign,code='private-foreign',name='Foreign type')
    client.force_authenticate(owner)
    public = client.get('/api/v1/form-templates/request_types/')
    assert public.status_code == 200, public.data
    assert len(public.data) == 1
    for field in ('description','sensitive','amount_required','quantity_required','needed_by_required','attachments_allowed','attachments_required'):
        assert public.data[0][field] == payload[field]
    assert client.post('/api/v1/company-setup/request-types/', payload, format='json').status_code == 403

@pytest.mark.django_db
def test_request_draft_can_be_completed_and_required_files_added_securely(request_policy_workspace):
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    definition = RequestTypeDefinition.objects.create(company=home,code='evidence',name='Evidence request',sensitive=True,amount_enabled=True,amount_required=True,quantity_enabled=True,quantity_required=True,needed_by_required=True,attachments_required=True,workflow=route)
    client.force_authenticate(owner)
    created = client.post('/api/v1/business-requests/', {'request_type':definition.code,'title':'Supplies','description':'Test draft'}, format='json')
    assert created.status_code == 201, created.data
    obj = BusinessRequest.objects.get(pk=created.data['id'])
    assert obj.status == 'DRAFT' and obj.request_type_snapshot['sensitive']
    assert created.data['attachment_policy'] == {'allowed':True,'required':True}
    with pytest.raises(ValidationError): BusinessRequestLifecycleService.validate_definition(obj)
    endpoint = f'/api/v1/business-requests/{obj.pk}/'
    result = client.patch(endpoint, {'amount':'50.00','currency':'USD','quantity':'2.00','unit':'boxes','needed_by':'2026-11-01'}, format='json')
    assert result.status_code == 200, result.data
    obj.refresh_from_db()
    with pytest.raises(ValidationError): BusinessRequestLifecycleService.validate_definition(obj)
    uploaded = client.post(endpoint+'attachments/', {'file':SimpleUploadedFile('evidence.txt',b'Synthetic evidence')}, format='multipart')
    assert uploaded.status_code == 201, uploaded.data
    assert uploaded.data['file'] is None and uploaded.data['file_url'] is None
    attachment_id = uploaded.data['id']
    assert BusinessRequestLifecycleService.validate_definition(obj).pk == definition.pk
    rows = client.get(endpoint+'attachments/'); assert len(rows.data) == 1
    downloaded = client.get(f'/api/v1/attachments/{attachment_id}/download/')
    assert downloaded.status_code == 200
    assert b''.join(downloaded.streaming_content) == b'Synthetic evidence'
    for denied in (peer,outsider):
        client.force_authenticate(denied)
        assert client.get(endpoint+'attachments/').status_code == 404
        assert client.get(f'/api/v1/attachments/{attachment_id}/download/').status_code == 404
    client.force_authenticate(owner)
    obj.status = 'SUBMITTED'; obj.save(update_fields=['status'])
    assert client.post(endpoint+'attachments/', {'file':SimpleUploadedFile('later.txt',b'Late evidence')}, format='multipart').status_code == 403
    assert client.delete(f'/api/v1/attachments/{attachment_id}/').status_code == 400

@pytest.mark.django_db
def test_request_file_policy_and_storage_cannot_be_bypassed(request_policy_workspace, monkeypatch):
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    definition = RequestTypeDefinition.objects.create(company=home,code='no-files',name='No file request',attachments_allowed=False)
    obj = BusinessRequest.objects.create(company=home,requester=owner,request_type=definition.code,request_type_definition=definition,request_number='Policy-file',title='Test',description='Test')
    endpoint = f'/api/v1/business-requests/{obj.pk}/attachments/'
    client.force_authenticate(owner)
    assert client.post(endpoint, {'file':SimpleUploadedFile('test.txt',b'Test')}, format='multipart').status_code == 403
    definition.attachments_allowed=True; definition.save(update_fields=['attachments_allowed'])
    assert client.post(endpoint, {'file':SimpleUploadedFile('test.exe',b'Test')}, format='multipart').status_code == 400
    monkeypatch.setattr(SubscriptionService,'can_upload',lambda company,additional_bytes=0:False)
    assert client.post(endpoint, {'file':SimpleUploadedFile('test.txt',b'Test')}, format='multipart').status_code == 400

@pytest.mark.django_db
def test_request_approval_route_can_be_created_from_company_setup(request_policy_workspace):
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    payload = {'name':'New company request route','target_type':'REQUEST','steps':[{'order':1,'label':'Review request','recipient':{'type':'USER','user_id':str(admin.pk)},'notify_email':False}]}
    result = client.post('/api/v1/company-setup/approval-routes/', payload, format='json')
    assert result.status_code == 201, result.data
    assert result.data['target_type'] == 'REQUEST'
    assert WorkflowDefinition.objects.get(pk=result.data['workflow']).target_type == 'REQUEST'
    assert client.patch(f"/api/v1/company-setup/approval-routes/{result.data['id']}/", {'target_type':'FORM_SUBMISSION'}, format='json').status_code == 400
    legacy = client.post('/api/v1/company-setup/approval-routes/', {**payload,'name':'Legacy form route','target_type':'FORM_SUBMISSION'}, format='json')
    assert legacy.status_code == 201 and legacy.data['target_type'] == 'FORM_SUBMISSION'
    choices = client.get('/api/v1/company-setup/request-types/approval-choices/')
    assert result.data['workflow'] in {row['id'] for row in choices.data}
    assert legacy.data['workflow'] not in {row['id'] for row in choices.data}

@pytest.mark.django_db
def test_request_uses_trusted_branch_and_can_reach_approval(request_policy_workspace):
    from companies.models import Branch
    from organizations.models import UserCapabilityGrant
    from workflows.models import WorkflowStepDefinition
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    branch = Branch.objects.create(company=home,name='Request filing branch')
    owner.branch=branch;owner.save(update_fields=['branch'])
    UserCapabilityGrant.objects.create(company=home,user=admin,capability='APPROVE_REQUESTS')
    WorkflowStepDefinition.objects.create(workflow=route,name='Review request',order=1,recipient_type='USER',recipient_user=admin,notify_email=False)
    definition = RequestTypeDefinition.objects.create(company=home,code='ready-request',name='Ready request',workflow=route)
    client.force_authenticate(owner)
    created = client.post('/api/v1/business-requests/', {'request_type':definition.code,'title':'Test request','description':'Synthetic workflow test'}, format='json')
    assert created.status_code == 201, created.data
    assert created.data['branch'] == branch.pk and created.data['branch_name'] == branch.name
    result = client.post(f"/api/v1/business-requests/{created.data['id']}/submit/", {}, format='json')
    assert result.status_code == 200, result.data

@pytest.mark.django_db
def test_request_linked_form_keeps_its_filing_context(request_policy_workspace):
    from companies.models import Branch
    from forms_engine.models import FormTemplate,FormSubmission
    home, foreign, admin, owner, peer, outsider, route, client = request_policy_workspace
    branch = Branch.objects.create(company=home,name='Linked request branch')
    other = Branch.objects.create(company=home,name='Other request branch')
    owner.branch=branch;owner.save(update_fields=['branch'])
    template = FormTemplate.objects.create(company=home,branch=branch,name='Additional request form',code='request-additional',lifecycle_status='PUBLISHED')
    definition = RequestTypeDefinition.objects.create(company=home,code='linked-request',name='Linked request',form_template=template)
    client.force_authenticate(owner)
    before = FormSubmission.objects.count()
    denied = client.post('/api/v1/business-requests/', {'request_type':definition.code,'title':'Test','description':'Test','branch':other.pk},format='json')
    assert denied.status_code == 400, denied.data
    assert FormSubmission.objects.count() == before
    created = client.post('/api/v1/business-requests/', {'request_type':definition.code,'title':'Test','description':'Test'},format='json')
    assert created.status_code == 201, created.data
    obj = BusinessRequest.objects.get(pk=created.data['id'])
    assert obj.branch_id == obj.form_submission.branch_id == branch.pk
    assert client.post(f'/api/v1/business-requests/{obj.pk}/attachments/', {'file':SimpleUploadedFile('test.txt',b'Test')}, format='multipart').status_code == 403
