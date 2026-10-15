from datetime import time, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company, Branch
from company_setup.models import CompanySetupState
from company_setup.setup_contract import SETUP_VERSION
from reporting_schedules.models import ReportingObligation, ReportingSchedule
from forms_engine.models import FormTemplate, FormSubmission
from workflows.models import WorkflowDefinition, WorkflowStepDefinition


@pytest.fixture
def journey(django_user_model):
    company = Company.objects.create(name="Isolated reporting journey")
    CompanySetupState.objects.create(company=company, onboarding_completed=True, setup_version=SETUP_VERSION)
    branch = Branch.objects.create(company=company, name="North")
    other_branch = Branch.objects.create(company=company, name="South")
    users = {}
    for name, role, location in [("author", "ADMIN", branch), ("reviewer", "MANAGER", branch), ("employee", "EMPLOYEE", branch), ("peer", "EMPLOYEE", other_branch)]:
        users[name] = django_user_model.objects.create_user(email=f"{name}@journey.test", full_name=name,
            company=company, branch=location, role=role, is_active=True, account_state="ACTIVE", email_verified=True)
    workflow = WorkflowDefinition.objects.create(company=company, name="Review daily report", code="journey", target_type="FORM_SUBMISSION")
    WorkflowStepDefinition.objects.create(workflow=workflow, name="Manager review", order=1,
        recipient_type="USER", recipient_user=users["reviewer"], notify_email=False)
    template = FormTemplate.objects.create(company=company, name="Daily report", code="journey", lifecycle_status="PUBLISHED", workflow=workflow)
    schedule = ReportingSchedule.objects.create(company=company, template=template, name="Daily operations", frequency="DAILY",
        target_type="USER", target_user=users["author"], start_date=timezone.localdate(), due_time=time(17))
    obligations = {}
    for name, user in users.items():
        obligations[name] = ReportingObligation.objects.create(company=company, schedule=schedule, user=user,
            reporting_date=timezone.localdate(), due_at=timezone.now()+timedelta(days=1))
    client = APIClient()
    return client, users, obligations


@pytest.mark.django_db
def test_employee_manager_personal_lists_and_cross_author_start(journey):
    client, users, obligations = journey
    for name in ["employee", "reviewer", "author"]:
        client.force_authenticate(users[name])
        response = client.get('/api/v1/reporting-obligations/mine/')
        assert response.status_code == 200, response.data
        assert [str(row['id']) for row in response.data] == [str(obligations[name].pk)]
        assert response.data[0]['template_name'] == 'Daily report'
    client.force_authenticate(users['reviewer'])
    response = client.post(f'/api/v1/reporting-obligations/{obligations["author"].pk}/start/')
    assert response.status_code in (400, 403), response.data
    assert not FormSubmission.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('decision,status', [('approve','APPROVED'), ('return','RETURNED'), ('reject','REJECTED')])
@pytest.mark.parametrize('review_role', ['EMPLOYEE', 'MANAGER'])
def test_populated_report_and_approval_api(journey, decision, status, review_role, django_user_model):
    client, users, obligations = journey
    users['reviewer'].role = review_role
    users['reviewer'].save(update_fields=['role'])
    client.force_authenticate(users['author'])
    url = f'/api/v1/reporting-obligations/{obligations["author"].pk}/start/'
    response = client.post(url)
    assert response.status_code == 200, response.data
    submission_id = response.data['submission_id']
    assert client.post(url).data['submission_id'] == submission_id
    response = client.post(f'/api/v1/form-submissions/{submission_id}/submit/')
    assert response.status_code == 200, response.data
    from workflows.models import WorkflowInstance
    instance = WorkflowInstance.objects.get(object_id=submission_id)
    detail = f'/api/v1/workflow-instances/{instance.pk}/'
    response = client.get(detail)
    assert response.status_code == 200, response.data
    assert response.data['allowed_actions'] == []
    client.force_authenticate(users['employee'])
    assert client.get(detail).status_code == 404
    assert client.post(detail+decision+'/', {'note':'Not assigned'}, format='json').status_code == 404
    other = Company.objects.create(name='Other isolated company')
    outsider = django_user_model.objects.create_user(email='outsider@journey.test', company=other,
        role='ADMIN', is_active=True, account_state='ACTIVE', email_verified=True)
    client.force_authenticate(outsider)
    assert client.get(detail).status_code == 404
    assert client.post(detail+decision+'/', {'note':'Other company'}, format='json').status_code == 404
    client.force_authenticate(users['reviewer'])
    response = client.get(detail)
    assert response.status_code == 200, response.data
    assert response.data['allowed_actions'] == ['APPROVE','RETURN','REJECT']
    assert response.data['current_step']['name'] == 'Manager review'
    if decision != 'approve':
        assert client.post(detail+decision+'/', {'note':''}, format='json').status_code == 400
    assert client.post(detail+decision+'/', {'note':'Reviewed in isolated test'}, format='json').status_code == 200
    instance.refresh_from_db()
    assert instance.status == status
    obligations['author'].refresh_from_db()
    assert obligations['author'].status == status
    assert client.get(detail).data['allowed_actions'] == []
    assert client.post(detail+decision+'/', {'note':'Duplicate'}, format='json').status_code == 400
    from notifications.models import Notification
    notification = Notification.objects.get(recipient=users['author'], notification_type='REQUEST_UPDATE')
    assert notification.company_id == users['author'].company_id
    assert notification.url == f'/forms/submissions/{submission_id}'
    assert 'Reviewed in isolated test' not in notification.message
    review_notification = Notification.objects.get(recipient=users['reviewer'], notification_type='WORKFLOW_ACTION')
    assert review_notification.url == f'/approvals/{instance.pk}'
    if decision == 'return':
        client.force_authenticate(users['author'])
        returned = client.get(f'/api/v1/form-submissions/{submission_id}/')
        assert returned.status_code == 200
        assert returned.data['return_note'] == 'Reviewed in isolated test'
        assert client.post(url).data['submission_id'] == submission_id
        assert client.post(f'/api/v1/form-submissions/{submission_id}/submit/').status_code == 200
        obligations['author'].refresh_from_db()
        assert obligations['author'].status == 'SUBMITTED'


@pytest.mark.django_db
def test_disabled_decisions_are_not_offered_or_accepted(journey):
    client, users, obligations = journey
    client.force_authenticate(users['author'])
    start = client.post(f'/api/v1/reporting-obligations/{obligations["author"].pk}/start/')
    submission_id = start.data['submission_id']
    assert client.post(f'/api/v1/form-submissions/{submission_id}/submit/').status_code == 200
    from workflows.models import WorkflowInstance
    instance = WorkflowInstance.objects.get(object_id=submission_id)
    step = instance.steps.get()
    step.can_return = step.can_reject = False
    step.save(update_fields=['can_return', 'can_reject'])
    detail = f'/api/v1/workflow-instances/{instance.pk}/'
    client.force_authenticate(users['reviewer'])
    assert client.get(detail).data['allowed_actions'] == ['APPROVE']
    for action in ['return', 'reject']:
        assert client.post(detail+action+'/', {'note':'Disabled decision'}, format='json').status_code == 400
    instance.refresh_from_db()
    assert instance.status == 'IN_PROGRESS'


@pytest.mark.django_db
def test_decision_notification_respects_author_in_app_preference(journey):
    from notifications.models import Notification, NotificationPreference
    from workflows.models import WorkflowInstance
    client, users, obligations = journey
    NotificationPreference.objects.update_or_create(user=users['author'], defaults={'in_app_enabled': False})
    client.force_authenticate(users['author'])
    started = client.post(f'/api/v1/reporting-obligations/{obligations["author"].pk}/start/')
    submission_id = started.data['submission_id']
    assert client.post(f'/api/v1/form-submissions/{submission_id}/submit/').status_code == 200
    instance = WorkflowInstance.objects.get(object_id=submission_id)
    client.force_authenticate(users['reviewer'])
    assert client.post(f'/api/v1/workflow-instances/{instance.pk}/approve/', {'note': ''}, format='json').status_code == 200
    assert not Notification.objects.filter(recipient=users['author']).exists()


@pytest.mark.django_db
@pytest.mark.parametrize('variant', ['active', 'expired', 'cancelled', 'future', 'wrong_permission'])
def test_delegated_form_review_matches_permission_and_validity(journey, variant):
    from forms_engine.models import FormSubmission
    from organizations.models import EmployeeDelegation
    from workflows.models import WorkflowInstance, WorkflowActionLog
    client, users, obligations = journey
    client.force_authenticate(users['author'])
    started = client.post(f'/api/v1/reporting-obligations/{obligations["author"].pk}/start/')
    submission_id = started.data['submission_id']
    assert client.post(f'/api/v1/form-submissions/{submission_id}/submit/').status_code == 200
    instance = WorkflowInstance.objects.get(object_id=submission_id)
    submission = FormSubmission.objects.get(pk=submission_id)
    submission.schema_snapshot['fields'].append({
        'key': 'salary', 'label': 'Salary', 'field_type': 'DECIMAL',
        'classification': 'COMPENSATION',
    })
    submission.data['salary'] = '500'
    submission.save(update_fields=['schema_snapshot', 'data'])
    now = timezone.now()
    delegation = EmployeeDelegation.objects.create(
        company=users['author'].company, from_user=users['reviewer'], to_user=users['employee'],
        permissions=['APPROVE_REPORTS' if variant == 'wrong_permission' else 'REVIEW_SUBMISSIONS'],
        starts_at=now + timedelta(days=1) if variant == 'future' else now - timedelta(days=2),
        ends_at=now - timedelta(days=1) if variant == 'expired' else now + timedelta(days=2),
        status='CANCELLED' if variant == 'cancelled' else 'ACTIVE',
    )
    client.force_authenticate(users['employee'])
    detail = f'/api/v1/workflow-instances/{instance.pk}/'
    response = client.get(detail)
    if variant != 'active':
        assert response.status_code == 404, response.data
        assert client.get(f'/api/v1/form-submissions/{submission_id}/').status_code == 404
        assert client.post(detail+'approve/', {'note': 'Attempted review'}, format='json').status_code == 404
        instance.refresh_from_db()
        assert instance.status == 'IN_PROGRESS'
        submission.refresh_from_db()
        assert submission.data['salary'] == '500'
        return
    assert response.status_code == 200, response.data
    assert response.data['allowed_actions'] == ['APPROVE', 'RETURN', 'REJECT']
    assert response.data['delegated'] is True
    source = client.get(f'/api/v1/form-submissions/{submission_id}/')
    assert source.status_code == 200, source.data
    assert source.data['data']['salary'] == '[REDACTED]'
    denied_edit = client.patch(f'/api/v1/form-submissions/{submission_id}/', {
        'data': {'salary': '999'},
    }, format='json')
    assert denied_edit.status_code == 400, denied_edit.data
    assert 'Only draft or returned submissions' in str(denied_edit.data)
    submission.refresh_from_db()
    assert submission.data['salary'] == '500'
    assert client.post(detail+'approve/', {'note': 'Delegated review'}, format='json').status_code == 200
    log = WorkflowActionLog.objects.get(workflow_instance=instance, action='APPROVED')
    assert log.actor_id == users['employee'].pk
    assert log.metadata['delegated'] is True
    assert log.metadata['acting_for_user_id'] == str(users['reviewer'].pk)
    delegation.status = 'CANCELLED'
    delegation.save(update_fields=['status'])
    assert client.get(detail).status_code == 404
    assert client.get(f'/api/v1/form-submissions/{submission_id}/').status_code == 404
