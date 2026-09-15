import pytest
from types import SimpleNamespace
from rest_framework.test import APIClient
from companies.models import Company
from subscriptions.models import Plan, Subscription
from security.models import AuditLog
from core.admin_site import RecoveryAdminSite

@pytest.mark.parametrize('staff,superuser,active,deleted,allowed', [(True,False,True,False,False),(True,True,True,False,True),(True,True,False,False,False),(True,True,True,True,False),(False,True,True,False,False)])
def test_recovery_admin_boundary(staff,superuser,active,deleted,allowed):
    user=SimpleNamespace(is_staff=staff,is_superuser=superuser,is_active=active,is_deleted=deleted)
    assert RecoveryAdminSite().has_permission(SimpleNamespace(user=user)) is allowed

@pytest.mark.django_db
def test_platform_subscription_contract_and_change(django_user_model):
    company=Company.objects.create(name='Subscription test')
    actor=django_user_model.objects.create_superuser(email='platform-plan@example.test',full_name='Test platform admin',password='test-password')
    tenant=django_user_model.objects.create_user(email='tenant-plan@example.test',password='test-password',company=company,role='ADMIN')
    old=Plan.objects.create(name='Old',max_users=10,max_projects=10,price_monthly=10)
    new=Plan.objects.create(name='New',max_users=20,max_projects=20,price_monthly=20)
    inactive=Plan.objects.create(name='Inactive',max_users=20,max_projects=20,price_monthly=20,is_active=False)
    subscription=Subscription.objects.create(company=company,plan=old)
    client=APIClient()
    url=f'/api/platform/v1/subscriptions/{subscription.pk}/change-plan/'
    assert client.get('/api/platform/v1/plans/').status_code==401
    client.force_authenticate(tenant)
    assert client.get('/api/platform/v1/plans/').status_code==403
    assert client.post(url,{'plan_id':new.pk,'reason':'Upgrade'}).status_code==403
    client.force_authenticate(actor)
    response=client.get(f'/api/platform/v1/subscriptions/{subscription.pk}/')
    assert response.status_code==200, response.data
    assert response.data['company_name']==company.name
    assert response.data['users_used']==1
    assert response.data['plan_name']=='Old'
    for payload in [{'plan_id':new.pk,'reason':' '},{'plan_id':'invalid','reason':'Upgrade'},{'plan_id':inactive.pk,'reason':'Upgrade'},{'plan_id':new.pk,'reason':None}]:
        assert client.post(url,payload,format='json').status_code==400
    response=client.post(url,{'plan_id':new.pk,'reason':'Capacity increase'},format='json')
    assert response.status_code==200, response.data
    subscription.refresh_from_db()
    assert subscription.plan_id==new.pk
    assert AuditLog.objects.filter(object_id=str(subscription.pk),metadata__new_plan_id=new.pk).exists()
    tiny=Plan.objects.create(name='Tiny',max_users=0,max_projects=0,price_monthly=0)
    assert client.post(url,{'plan_id':tiny.pk,'reason':'Downgrade'},format='json').status_code==400
    subscription.refresh_from_db()
    assert subscription.plan_id==new.pk


@pytest.mark.django_db
def test_personal_security_is_owner_scoped(django_user_model):
    from security.models import ActiveSession, TrustedDevice
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
    company = Company.objects.create(name='Security owner test')
    owner = django_user_model.objects.create_user(email='owner@example.test', password='x', company=company)
    other = django_user_model.objects.create_user(email='other@example.test', password='x', company=company)
    refresh = RefreshToken.for_user(owner)
    own = ActiveSession.objects.create(user=owner, company=company, refresh_token_jti=refresh['jti'], ip_address='127.0.0.1')
    foreign = ActiveSession.objects.create(user=other, company=company, refresh_token_jti='foreign', ip_address='127.0.0.1')
    device = TrustedDevice.objects.create(user=owner, token_hash='a'*64, device_name='Test browser')
    other_device = TrustedDevice.objects.create(user=other, token_hash='b'*64, device_name='Other browser')
    client = APIClient()
    client.force_authenticate(owner)
    response = client.get('/api/v1/security/sessions/')
    assert response.status_code == 200
    assert [item['id'] for item in response.data['results']] == [str(own.pk)]
    assert response.data['results'][0]['allowed_actions'] == ['REVOKE']
    assert client.post(f'/api/v1/security/sessions/{foreign.pk}/revoke/').status_code == 404
    assert client.post(f'/api/v1/security/trusted-devices/{other_device.pk}/revoke/').status_code == 404
    assert client.post(f'/api/v1/security/sessions/{own.pk}/revoke/').status_code == 200
    assert BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists()
    assert client.post(f'/api/v1/security/trusted-devices/{device.pk}/revoke/').status_code == 200
    device.refresh_from_db()
    assert not device.is_active and device.revoked_by_id == owner.pk
    assert client.post('/api/v1/security/trusted-devices/', {'device_name': 'Unsafe'}).status_code == 405


def test_platform_support_route_uses_existing_guarded_view():
    from django.urls import resolve
    from support.views import PlatformSupportTicketViewSet
    assert resolve('/api/platform/v1/support/tickets/').func.cls is PlatformSupportTicketViewSet

@pytest.mark.django_db
def test_company_configuration_boundary(django_user_model):
    from company_setup.models import RequestTypeDefinition, RolePreset
    from core.capabilities import Capabilities
    company = Company.objects.create(name='Configuration A')
    other_company = Company.objects.create(name='Configuration B')
    admin = django_user_model.objects.create_user(email='setup-admin@example.test', password='x', company=company, role='ADMIN')
    employee = django_user_model.objects.create_user(email='setup-employee@example.test', password='x', company=company, role='EMPLOYEE')
    platform = django_user_model.objects.create_superuser(email='setup-platform@example.test', full_name='Platform', password='x')
    foreign = RequestTypeDefinition.objects.create(company=other_company, code='foreign', name='Foreign')
    client = APIClient()
    url = '/api/v1/company-setup/request-types/'
    for user in [employee, platform]:
        client.force_authenticate(user)
        assert client.get(url).status_code == 403
        assert client.post(url, {'code': 'no', 'name': 'No'}).status_code == 403
    client.force_authenticate(admin)
    response = client.post(url, {'code': 'travel', 'name': 'Travel', 'company': other_company.pk}, format='json')
    assert response.status_code == 201, response.data
    assert RequestTypeDefinition.objects.get(pk=response.data['id']).company_id == company.pk
    assert client.patch(f'{url}{foreign.pk}/', {'name': 'Changed'}).status_code == 404
    assert client.post(f'{url}{response.data["id"]}/deactivate/').status_code == 200
    response = client.post('/api/v1/company-setup/role-presets/', {'code': 'bad', 'name': 'Bad', 'capabilities': list(Capabilities.PLATFORM_ONLY)}, format='json')
    assert response.status_code == 400
    assert not RolePreset.objects.filter(company=company, code='bad').exists()
    response = client.get('/api/v1/company-setup/capabilities/')
    assert response.status_code == 200
    assert all(item['tenant_assignable'] for item in response.data)
