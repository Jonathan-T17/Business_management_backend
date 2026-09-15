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
