import pytest
from rest_framework.test import APIClient
from companies.models import Company
from organizations.models import Position
from company_setup.models import ReportingProcess, ApprovalRoute
from forms_engine.models import FormTemplate
from reporting_schedules.models import ReportingSchedule
from workflows.models import WorkflowDefinition

@pytest.mark.django_db
def test_reporting_composition_and_activation(django_user_model):
    company = Company.objects.create(name='Reporting company')
    other = Company.objects.create(name='Other')
    actor = django_user_model.objects.create_user(email='report-config@example.test',company=company,role='ADMIN',account_state='ACTIVE')
    position = Position.objects.create(company=company,title='Reporter')
    foreign = Position.objects.create(company=other,title='Foreign')
    client = APIClient(); client.force_authenticate(actor)
    url = '/api/v1/company-setup/reporting-processes/'
    payload = {'name':'Weekly report','submitters':{'type':'POSITION','position_id':position.pk},'schedule':{'frequency':'WEEKLY','due_time':'17:30','weekday':4},'fields':[{'key':'summary','label':'Summary','type':'LONG_TEXT','required':True}],'approval_route':[{'order':1,'label':'Review','recipient':{'type':'POSITION','position_id':position.pk}}]}
    bad = {**payload,'submitters':{'type':'POSITION','position_id':foreign.pk}}
    assert client.post(url,bad,format='json').status_code == 400
    assert not FormTemplate.objects.exists()
    bad = {**payload,'schedule':{'frequency':'WEEKLY','due_time':'17:30'}}
    assert client.post(url,bad,format='json').status_code == 400
    bad = {**payload,'fields':payload['fields']*2}
    assert client.post(url,bad,format='json').status_code == 400
    from unittest.mock import patch
    with patch('company_setup.reporting_views.ReportingProcessViewSet.audit', side_effect=RuntimeError('Audit unavailable')):
        with pytest.raises(RuntimeError):
            client.post(url,payload,format='json')
    assert not FormTemplate.objects.exists()
    assert not ReportingSchedule.objects.exists()
    assert not WorkflowDefinition.objects.exists()
    response = client.post(url,payload,format='json')
    assert response.status_code == 201, response.data
    assert response.data['schedule']['weekday'] == 4
    assert len(response.data['approval_route']) == 1
    assert not response.data['is_active']
    process = ReportingProcess.objects.get(pk=response.data['id'])
    assert process.schedule.template.lifecycle_status == 'DRAFT'
    assert not process.schedule.is_active
    detail = url+str(process.pk)+'/'
    assert client.patch(detail,{'is_active':True},format='json').status_code == 400
    response = client.patch(detail,{'schedule':{'due_time':'18:00'}},format='json')
    assert response.status_code == 200, response.data
    assert response.data['schedule']['weekday'] == 4
    counts = (FormTemplate.objects.count(), ReportingSchedule.objects.count(), WorkflowDefinition.objects.count(), ApprovalRoute.objects.count())
    assert client.post(url,payload,format='json').status_code == 400
    assert counts == (FormTemplate.objects.count(), ReportingSchedule.objects.count(), WorkflowDefinition.objects.count(), ApprovalRoute.objects.count())
    template = process.schedule.template
    template.lifecycle_status = 'PUBLISHED'; template.save()
    assert client.patch(detail,{'is_active':True},format='json').status_code == 200
    process.refresh_from_db(); process.schedule.refresh_from_db()
    assert process.is_active and process.schedule.is_active
    actor.company = other; actor.save()
    assert client.get(detail).status_code == 404
    actor.role = 'EMPLOYEE'; actor.save()
    assert client.post(url,payload,format='json').status_code == 403
    actor.role = 'SUPERUSER'; actor.save()
    assert client.get(url).status_code == 403
