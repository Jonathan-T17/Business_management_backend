import pytest
from rest_framework.test import APIClient
from companies.models import Company
from organizations.models import Position
from company_setup.models import ApprovalRoute
from workflows.models import WorkflowDefinition, WorkflowInstance
from django.contrib.contenttypes.models import ContentType

@pytest.mark.django_db
def test_approval_configuration_preview_tenant_boundary_and_history(django_user_model):
    company = Company.objects.create(name='Approval company')
    other = Company.objects.create(name='Other company')
    actor = django_user_model.objects.create_user(email='route@example.test', company=company, role='ADMIN', is_active=True, account_state='ACTIVE')
    position = Position.objects.create(company=company, title='Reviewer')
    foreign = Position.objects.create(company=other, title='Other reviewer')
    client = APIClient()
    client.force_authenticate(actor)
    url = '/api/v1/company-setup/approval-routes/'
    payload = {'name':'Review route','steps':[{'order':1,'label':'Review','recipient':{'type':'POSITION','position_id':position.pk}}]}
    response = client.post(url+'preview/', payload, format='json')
    assert response.status_code == 200, response.data
    assert not ApprovalRoute.objects.exists()
    response = client.post(url, payload, format='json')
    assert response.status_code == 201, response.data
    route = ApprovalRoute.objects.get(pk=response.data['id'])
    assert response.data['steps'][0]['recipient']['position_id'] == str(position.pk)
    detail = url+str(route.pk)+'/'
    payload['steps'][0]['recipient']['position_id'] = foreign.pk
    assert client.patch(detail, {'steps':payload['steps']}, format='json').status_code == 400
    assert route.workflow.steps.get().recipient_position_id == position.pk
    assert client.patch(detail, {'steps':[{'order':1}]}, format='json').status_code == 400
    response = client.patch(detail, {'is_active':False}, format='json')
    assert response.status_code == 200, response.data
    route.workflow.refresh_from_db()
    assert not route.workflow.is_active
    payload['steps'][0]['recipient']['position_id'] = position.pk
    response = client.patch(detail, {'steps':payload['steps']}, format='json')
    assert response.status_code == 200, response.data
    WorkflowInstance.objects.create(company=company, workflow=route.workflow, content_type=ContentType.objects.get_for_model(Company), object_id=str(company.pk), submitted_by=actor)
    assert client.patch(detail, {'steps':payload['steps']}, format='json').status_code == 400
    before = WorkflowDefinition.objects.count()
    assert client.post(url, payload, format='json').status_code == 400
    assert WorkflowDefinition.objects.count() == before
    actor.company = other
    actor.save()
    assert client.get(detail).status_code == 404
    actor.role = 'EMPLOYEE'
    actor.save()
    assert client.post(url, payload, format='json').status_code == 403
    actor.role = 'SUPERUSER'
    actor.save()
    assert client.get(url).status_code == 403
