import pytest
from rest_framework.test import APIClient
from companies.models import Company
from company_setup.models import NotificationPolicy


@pytest.mark.django_db
def test_company_notification_rules_paging_update_and_boundaries(django_user_model):
    home=Company.objects.create(name='Rules home')
    other=Company.objects.create(name='Rules other')
    admin=django_user_model.objects.create_user(email='rule-admin@example.test',company=home,role='ADMIN')
    employee=django_user_model.objects.create_user(email='rule-employee@example.test',company=home,role='EMPLOYEE')
    for index in range(26):
        NotificationPolicy.objects.create(company=home,event_code=f'TEST_EVENT_{index}')
    foreign=NotificationPolicy.objects.create(company=other,event_code='PRIVATE_OTHER',email_enabled=True)
    client=APIClient();client.force_authenticate(admin)
    endpoint='/api/v1/company-setup/notification-policies/'
    first=client.get(endpoint);assert first.status_code==200,first.data
    assert first.data['count']==26 and len(first.data['results'])==25
    second=client.get(endpoint,{'page':2});assert len(second.data['results'])==1
    target=first.data['results'][0]['id']
    response=client.patch(f'{endpoint}{target}/',{'in_app_enabled':False,'email_enabled':False,'user_can_disable_email':False,'is_active':False},format='json')
    assert response.status_code==200,response.data
    for field in ('in_app_enabled','email_enabled','user_can_disable_email','is_active'):
        assert response.data[field] is False
    assert client.patch(f'{endpoint}{foreign.pk}/',{'email_enabled':False},format='json').status_code==404
    foreign.refresh_from_db();assert foreign.email_enabled is True
    client.force_authenticate(employee)
    assert client.get(endpoint).status_code==403
    assert client.patch(f'{endpoint}{target}/',{'email_enabled':True},format='json').status_code==403
