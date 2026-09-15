import pytest
from rest_framework.test import APIClient
from companies.models import Company
from planning.models import CompanyPlan, PlanItem
from security.models import AuditLog

@pytest.mark.django_db
def test_plan_lifecycle_and_scope(django_user_model):
    company = Company.objects.create(name='Planning tenant')
    other = Company.objects.create(name='Other planning tenant')
    admin = django_user_model.objects.create_user(email='planner@example.test',company=company,role='ADMIN')
    reader = django_user_model.objects.create_user(email='viewer@example.test',company=company,role='EMPLOYEE')
    client = APIClient(); client.force_authenticate(admin)
    payload = {'title':'Monthly plan','plan_type':'MONTHLY','visibility':'COMPANY','start_date':'2026-09-01','end_date':'2026-09-30'}
    response = client.post('/api/v1/company-plans/',payload)
    assert response.status_code == 201, response.data
    url = f"/api/v1/company-plans/{response.data['id']}/"
    plan = CompanyPlan.objects.get(pk=response.data['id'])
    PlanItem.objects.create(plan=plan,title='Finished',status='COMPLETED')
    PlanItem.objects.create(plan=plan,title='Blocked',status='BLOCKED')
    response = client.get(url)
    assert response.data['progress'] == 50
    assert response.data['at_risk_items'] == 1
    assert 'ACTIVATE' in response.data['allowed_actions']
    assert client.patch(url,{'status':'COMPLETED'}).status_code == 400
    assert client.patch(url,{'end_date':'2026-08-01'}).status_code == 400
    foreign = django_user_model.objects.create_user(email='foreign@example.test',company=other)
    assert client.patch(url,{'owner':foreign.pk}).status_code == 400
    client.force_authenticate(reader)
    assert client.get(url).data['allowed_actions'] == []
    assert client.post(url+'activate/').status_code == 403
    client.force_authenticate(admin)
    assert client.post(url+'complete/').status_code == 400
    assert client.post(url+'activate/').data['status'] == 'ACTIVE'
    assert client.post(url+'activate/').status_code == 400
    assert client.post(url+'complete/').data['status'] == 'COMPLETED'
    assert client.post(url+'archive/').data['allowed_actions'] == []
    assert AuditLog.objects.filter(object_id=str(plan.pk),action='UPDATE').count() == 3
    plan.company = other; plan.save()
    assert client.get(url).status_code == 404
    assert client.post(url+'cancel/').status_code == 404
    platform = django_user_model.objects.create_user(email='platform-planner@example.test',role='SUPERUSER',company=other)
    client.force_authenticate(platform)
    assert client.get(url).status_code == 404
