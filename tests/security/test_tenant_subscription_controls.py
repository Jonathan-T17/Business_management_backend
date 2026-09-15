import pytest
from rest_framework.test import APIClient
from companies.models import Company
from subscriptions.models import Plan, Subscription
from security.models import AuditLog

@pytest.mark.django_db
def test_tenant_subscription_controls(django_user_model):
    company=Company.objects.create(name='Subscription tenant')
    other=Company.objects.create(name='Other subscription tenant')
    actor=django_user_model.objects.create_user(email='subscriber@example.test',company=company,role='ADMIN')
    plan=Plan.objects.create(name='Tenant plan',max_users=10,max_projects=10,price_monthly=0)
    sub=Subscription.objects.create(company=company,plan=plan)
    foreign=Subscription.objects.create(company=other,plan=plan)
    client=APIClient();client.force_authenticate(actor)
    url=f'/api/v1/subscriptions/{sub.pk}/'
    assert client.get(url).data['allowed_actions'] == ['CANCEL']
    assert client.patch(url,{'plan_id':plan.pk,'expires_at':'2099-01-01T00:00:00Z'}).status_code == 405
    assert client.post('/api/v1/subscriptions/',{'plan_id':plan.pk}).status_code == 405
    assert client.delete(url).status_code == 405
    assert client.patch(f'/api/v1/plans/{plan.pk}/',{'price_monthly':0}).status_code == 405
    assert client.post(f'/api/v1/subscriptions/{foreign.pk}/cancel/',{'reason':'Wrong company'}).status_code == 404
    assert client.post(url+'cancel/').status_code == 400
    response=client.post(url+'cancel/',{'reason':'Company no longer needs service'})
    assert response.status_code == 200, response.data
    assert response.data['plan']['id'] == plan.pk
    assert response.data['is_active'] is False
    assert response.data['allowed_actions'] == []
    assert AuditLog.objects.filter(company=company,action='SUBSCRIPTION_CANCELLED',metadata__reason='Company no longer needs service').exists()
    assert client.post(url+'cancel/',{'reason':'Again'}).status_code == 400
    actor.role='EMPLOYEE';actor.save()
    assert client.get(url).status_code == 403
    actor.role='SUPERUSER';actor.save()
    assert client.get(url).status_code == 403
