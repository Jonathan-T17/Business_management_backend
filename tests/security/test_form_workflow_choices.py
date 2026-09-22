import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from companies.models import Company
from company_setup.models import CompanySetupState
from forms_engine.models import FormSubmission
from workflows.models import WorkflowDefinition, WorkflowStepDefinition, WorkflowInstance


@pytest.mark.django_db
def test_form_choices_publish_and_submit_use_active_workflows(django_user_model):
    company = Company.objects.create(name='Form workflow choices')
    other = Company.objects.create(name='Other workflow choices')
    author = django_user_model.objects.create_user(email='choices@example.test', company=company,
        role='ADMIN', is_active=True, account_state='ACTIVE', email_verified=True)
    reviewer = django_user_model.objects.create_user(email='reviewer-choices@example.test', company=company,
        role='ADMIN', is_active=True, account_state='ACTIVE')
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(author)}')
    active = WorkflowDefinition.objects.create(company=company, name='Form approval', code='form', target_type='FORM_SUBMISSION')
    inactive = WorkflowDefinition.objects.create(company=company, name='Inactive', code='inactive', target_type='FORM_SUBMISSION', is_active=False)
    WorkflowDefinition.objects.create(company=other, name='Private', code='private', target_type='FORM_SUBMISSION')
    WorkflowDefinition.objects.create(company=company, name='Report approval', code='report', target_type='REPORT')
    WorkflowStepDefinition.objects.create(workflow=active, name='Review', order=1,
        recipient_type='USER', recipient_user=reviewer, notify_email=False)
    root = '/api/v1/form-templates/'
    response = client.get(root+'choices/')
    assert response.status_code == 200, response.data
    assert response.data['workflows'] == [{'id':active.pk, 'name':active.name}]
    payload = {'name':'Working form', 'code':'working', 'workflow':active.pk,
        'fields':[{'key':'notes','label':'Notes','field_type':'TEXT','required':True}]}
    response = client.post(root, payload, format='json')
    assert response.status_code == 201, response.data
    template_id = response.data['id']
    assert client.post(root+template_id+'/publish/').status_code == 200
    # Runtime access only opens after setup; this fixture isolates the form journey.
    CompanySetupState.objects.create(company=company,onboarding_completed=True,setup_version=2)
    response = client.post('/api/v1/form-submissions/', {'template':template_id,'data':{'notes':'Checked'}}, format='json')
    assert response.status_code == 201, response.data
    submission_id = response.data['id']
    response = client.post(f'/api/v1/form-submissions/{submission_id}/submit/')
    assert response.status_code == 200, response.data
    assert WorkflowInstance.objects.filter(workflow=active,object_id=submission_id).exists()
    # Disabled routes fail cleanly at publish and submission, rather than raising AttributeError.
    payload.update(code='inactive-form', workflow=inactive.pk)
    response = client.post(root, payload, format='json')
    assert response.status_code == 201, response.data
    assert client.post(root+response.data['id']+'/publish/').status_code == 400
    response = client.post('/api/v1/form-submissions/', {'template':template_id,'data':{'notes':'Second'}}, format='json')
    assert response.status_code == 201, response.data
    active.is_active = False
    active.save(update_fields=['is_active'])
    assert client.post(f"/api/v1/form-submissions/{response.data['id']}/submit/").status_code == 400
    assert FormSubmission.objects.get(pk=response.data['id']).status == 'DRAFT'
