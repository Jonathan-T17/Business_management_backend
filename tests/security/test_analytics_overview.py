import pytest
from rest_framework.test import APIClient
from companies.models import Company, Branch
from projects.models import Project
from tasks.models import Task
from subscriptions.models import Plan, Subscription
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities

@pytest.mark.django_db
def test_analytics_overview_scope(django_user_model):
    company=Company.objects.create(name='Analytics test')
    other=Company.objects.create(name='Other analytics test')
    user=django_user_model.objects.create_user(email='analytics@example.test',company=company,role='EMPLOYEE')
    plan=Plan.objects.create(name='Analytics test',max_users=10,max_projects=10,price_monthly=0)
    subscription=Subscription.objects.create(company=company,plan=plan)
    project=Project.objects.create(company=company,name='Visible',created_by=user)
    hidden=Project.objects.create(company=company,name='Hidden')
    foreign=Project.objects.create(company=other,name='Foreign')
    for target in (project,hidden,foreign):
        Task.objects.create(company=target.company,project=target,title='Task',status='done')
    client=APIClient(); client.force_authenticate(user)
    url='/api/v1/analytics/overview/'
    assert client.get(url).status_code == 403
    UserCapabilityGrant.objects.create(company=company,user=user,capability=Capabilities.VIEW_COMPANY_ANALYTICS)
    response=client.get(url)
    assert response.status_code == 200, response.data
    assert response.data['tasks']['total'] == 1
    assert response.data['tasks']['done'] == 1
    from datetime import datetime, timezone
    Task.objects.filter(project=project).update(created_at=datetime(2026, 9, 5, 12, tzinfo=timezone.utc))
    assert client.get(url, {'start_date':'2026-09-05','end_date':'2026-09-05'}).data['tasks']['total'] == 1
    assert client.get(url, {'start_date':'2026-09-06'}).data['tasks']['total'] == 0
    assert client.get(url, {'end_date':'2026-09-04'}).data['tasks']['total'] == 0

    assert client.get(url,{'start_date':'invalid'}).status_code == 400
    assert client.get(url,{'start_date':'2026-10-01','end_date':'2026-09-01'}).status_code == 400
    assert client.get(url,{'department':1}).status_code == 400
    branch=Branch.objects.create(company=other,name='Foreign')
    assert client.get(url,{'branch':branch.pk}).status_code == 400
    subscription.is_active=False; subscription.save()
    assert client.get(url).status_code in (400,403)
    user.role='SUPERUSER'; user.save()
    assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_form_charts_keep_zero_days_waiting_dates_and_tenant_visibility(django_user_model):
    from datetime import datetime, timedelta, timezone as dt_timezone
    from django.utils import timezone
    from forms_engine.models import FormTemplate, FormSubmission, MaterialJourney, MaterialMovement

    company = Company.objects.create(name='Chart company')
    other = Company.objects.create(name='Private company')
    user = django_user_model.objects.create_user(email='chart-user@example.test', company=company, role='EMPLOYEE')
    stranger = django_user_model.objects.create_user(email='chart-stranger@example.test', company=other, role='EMPLOYEE')
    peer = django_user_model.objects.create_user(email='chart-peer@example.test', company=company, role='EMPLOYEE')
    plan = Plan.objects.create(name='Chart plan', max_users=10, max_projects=10, price_monthly=0)
    Subscription.objects.create(company=company, plan=plan)
    UserCapabilityGrant.objects.create(company=company, user=user, capability=Capabilities.VIEW_COMPANY_ANALYTICS)
    branch = Branch.objects.create(company=company, name='Visible branch')
    hidden_branch = Branch.objects.create(company=company, name='Private branch')
    template = FormTemplate.objects.create(company=company, name='Work report', code='chart-work')
    foreign_template = FormTemplate.objects.create(company=other, name='Private report', code='chart-private')
    now = timezone.now()
    for index, (status, age) in enumerate([('SUBMITTED', 1), ('UNDER_REVIEW', 3), ('SUBMITTED', 9), ('SUBMITTED', None), ('APPROVED', 1), ('RETURNED', 1), ('DRAFT', None)]):
        entry = FormSubmission.objects.create(company=company, template=template, submitted_by=user, branch=branch,
                                               reference_number=f'CHART-{index}', status=status,
                                               submitted_at=now-timedelta(days=age) if age else None)
        FormSubmission.objects.filter(pk=entry.pk).update(created_at=datetime(2026, 10, 1, 12, tzinfo=dt_timezone.utc))
        journey = MaterialJourney.objects.create(submission=entry, items=[{'id':'0','item':'Paper','unit':'boxes','quantity':'10'}],
                                                  approved={'0':'10'} if status == 'APPROVED' else {})
        if status == 'APPROVED':
            approved_journey = journey
    for actor, target in [(stranger, foreign_template), (peer, template)]:
        private_entry = FormSubmission.objects.create(company=actor.company, template=target, submitted_by=actor, branch=hidden_branch if actor == peer else None, status='SUBMITTED')
        MaterialJourney.objects.create(submission=private_entry, items=[{'id':'0','item':'Private','unit':'pieces','quantity':'1'}])
    client = APIClient(); client.force_authenticate(user)
    response = client.get('/api/v1/analytics/overview/', {'start_date':'2026-10-01', 'end_date':'2026-10-03'})
    assert response.status_code == 200, response.data
    data = response.data
    assert [point['value'] for point in data['submission_trend']] == [7, 0, 0]
    assert len(data['branch_activity']) == 1
    assert data['branch_activity'][0] == {'branch_id':branch.pk, 'name':'Visible branch', 'total':6,
                                        'awaiting_review':4, 'approved':1, 'returned':1, 'other':0}
    assert [band['value'] for band in data['review_age']] == [1, 1, 1, 1]
    assert data['materials']['Awaiting review'] == 4
    assert data['materials']['Awaiting delivery'] == 1
    assert data['materials']['Returned'] == 1
    assert sum(data['materials'].values()) == 6
    event = MaterialMovement.objects.create(journey=approved_journey, stage='RECEIPT', quantities={'0':'5'}, actor=user, template=template)
    partial = client.get('/api/v1/analytics/overview/').data['materials']
    assert partial['Partial fulfillment'] == 1
    MaterialMovement.objects.filter(pk=event.pk).update(quantities={'0':'10'})
    assert client.get('/api/v1/analytics/overview/').data['materials']['Completed'] == 1
    MaterialMovement.objects.create(journey=approved_journey, stage='RETURN', quantities={'0':'2'}, actor=user, template=template)
    assert client.get('/api/v1/analytics/overview/').data['materials']['Partial fulfillment'] == 1
    empty = client.get('/api/v1/analytics/overview/', {'branch':hidden_branch.pk})
    assert empty.status_code == 200
    assert empty.data['branch_activity'] == []
    assert not any(band['value'] for band in empty.data['review_age'])
    assert not any(empty.data['materials'].values())
    long_range = client.get('/api/v1/analytics/overview/', {'start_date':'2026-01-01', 'end_date':'2026-10-03'})
    assert len(long_range.data['submission_trend']) == 30
