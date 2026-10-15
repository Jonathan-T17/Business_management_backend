import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from companies.models import Company, Branch
from forms_engine.models import FormSubmission
from workflows.models import WorkflowDefinition, WorkflowStepDefinition


@pytest.mark.django_db
def test_return_correct_resubmit_approve_keeps_entry_file_and_access_boundaries(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr('subscriptions.services.SubscriptionService.can_upload', lambda *args, **kwargs: True)
    company = Company.objects.create(name='Correction cycle test')
    branch = Branch.objects.create(company=company, name='Test branch')
    admin = django_user_model.objects.create_user(email='cycle-admin@example.test', company=company, role='ADMIN', is_active=True)
    author = django_user_model.objects.create_user(email='cycle-author@example.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    reviewer = django_user_model.objects.create_user(email='cycle-reviewer@example.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    peer = django_user_model.objects.create_user(email='cycle-peer@example.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    foreign_company = Company.objects.create(name='Separate correction tenant')
    outsider = django_user_model.objects.create_user(email='cycle-outsider@example.test', company=foreign_company, role='ADMIN', is_active=True)
    route = WorkflowDefinition.objects.create(company=company, name='Test review', code='test-correction-cycle', target_type='FORM_SUBMISSION', is_active=True)
    WorkflowStepDefinition.objects.create(workflow=route, name='Manager review', order=1, recipient_type='USER', recipient_user=reviewer, notify_email=False)
    client = APIClient(); client.force_authenticate(admin)
    response = client.post('/api/v1/form-templates/', {'name':'Test work report', 'code':'test-correction-cycle', 'workflow':route.pk,
        'fields':[{'key':'work','label':'Work completed','field_type':'TEXT','required':True}]}, format='json')
    assert response.status_code == 201, response.data
    template_id = response.data['id']
    response = client.post(f'/api/v1/form-templates/{template_id}/publish/', {'audience':'BRANCHES','branch_ids':[branch.pk]}, format='json')
    assert response.status_code == 200, response.data
    client.force_authenticate(author)
    response = client.post('/api/v1/form-submissions/', {'template':template_id,'data':{'work':'Test work'}}, format='json')
    assert response.status_code == 201, response.data
    entry_id = response.data['id']; entry = f'/api/v1/form-submissions/{entry_id}/'
    files = entry + 'attachments/'
    response = client.post(files, {'file':SimpleUploadedFile('sample-receipt.txt', b'TEST ONLY receipt')}, format='multipart')
    assert response.status_code == 201, response.data
    file_id = response.data['id']
    FormSubmission.objects.filter(pk=entry_id).update(title='PRIVATE user-entered title must stay hidden')
    response = client.post(entry + 'submit/')
    assert response.status_code == 200, response.data
    first_review = response.data['workflow_instance']; review = f'/api/v1/workflow-instances/{first_review}/'
    client.force_authenticate(peer)
    assert client.get(entry).status_code == 404
    assert client.get(review).status_code == 404
    assert client.post(review + 'approve/', {'note':'Unauthorized'}, format='json').status_code in (403,404)
    client.force_authenticate(reviewer)
    assert client.get(entry).status_code == 200
    summary = client.get(review)
    assert summary.status_code == 200
    assert summary.data['title'] == 'Test work report'
    assert summary.data['workflow_name'] == 'Test review'
    assert 'PRIVATE user-entered title' not in str(summary.data)
    assert client.post(review + 'return/', {'note':''}, format='json').status_code == 400
    note = 'TEST ONLY: add Sample receipt verified, then resubmit.'
    response = client.post(review + 'return/', {'note':note}, format='json')
    assert response.status_code == 200, response.data
    client.force_authenticate(author)
    response = client.get(entry)
    assert response.data['status'] == 'RETURNED'
    assert response.data['return_note'] == note
    assert 'EDIT' in response.data['allowed_actions']
    assert len(client.get(files).data['files']) == 1
    response = client.patch(entry, {'data':{'work':'Test work. Sample receipt verified.'}}, format='json')
    assert response.status_code == 200, response.data
    response = client.post(entry + 'submit/')
    assert response.status_code == 200, response.data
    next_review = response.data['workflow_instance']
    assert next_review != first_review
    assert FormSubmission.objects.filter(company=company).count() == 1
    client.force_authenticate(reviewer)
    response = client.post(f'/api/v1/workflow-instances/{next_review}/approve/', {'note':'TEST ONLY verified'}, format='json')
    assert response.status_code == 200, response.data
    client.force_authenticate(author)
    response = client.get(entry)
    assert response.data['status'] == 'APPROVED'
    assert 'EDIT' not in response.data['allowed_actions']
    assert response.data['return_note'] is None
    assert len(client.get(files).data['files']) == 1
    assert client.delete(f'{files}{file_id}/').status_code == 403
    client.force_authenticate(reviewer)
    response = client.get(f'{files}{file_id}/')
    assert response.status_code == 200
    assert b''.join(response.streaming_content) == b'TEST ONLY receipt'
    for actor in (peer, outsider):
        client.force_authenticate(actor)
        assert client.get(review).status_code == 404
        assert client.get(entry).status_code == 404
        assert client.get(f'{files}{file_id}/').status_code == 404
