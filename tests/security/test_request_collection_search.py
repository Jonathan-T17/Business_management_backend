import pytest
from rest_framework.test import APIClient
from companies.models import Company
from requests_app.models import BusinessRequest


@pytest.mark.django_db
def test_request_search_and_paging_preserve_visibility(django_user_model):
    home = Company.objects.create(name='Collection home')
    foreign = Company.objects.create(name='Collection foreign')
    owner = django_user_model.objects.create_user(email='collection-owner@example.test', company=home, role='EMPLOYEE')
    peer = django_user_model.objects.create_user(email='collection-peer@example.test', company=home, role='EMPLOYEE')
    outsider = django_user_model.objects.create_user(email='collection-foreign@example.test', company=foreign, role='EMPLOYEE')
    for index in range(26):
        BusinessRequest.objects.create(company=home, requester=owner, title=f'Supplies {index}', request_number=f'OWN-{index:03}')
    BusinessRequest.objects.create(company=home, requester=peer, title='Supplies private', request_number='PEER-PRIVATE')
    BusinessRequest.objects.create(company=foreign, requester=outsider, title='Supplies foreign', request_number='FOREIGN-PRIVATE')
    client = APIClient()
    client.force_authenticate(owner)
    endpoint = '/api/v1/business-requests/'
    first = client.get(endpoint, {'search': 'supplies', 'page': 1})
    assert first.status_code == 200, first.data
    assert first.data['count'] == 26
    assert len(first.data['results']) == 25
    second = client.get(endpoint, {'search': 'supplies', 'page': 2})
    assert second.status_code == 200 and len(second.data['results']) == 1
    assert not ({row['id'] for row in first.data['results']} & {row['id'] for row in second.data['results']})
    reference = client.get(endpoint, {'search': 'OWN-025'})
    assert reference.data['count'] == 1
    assert reference.data['results'][0]['request_number'] == 'OWN-025'
    assert client.get(endpoint, {'search': 'PRIVATE'}).data['count'] == 0
    assert client.get(endpoint, {'search': 'no-match'}).data['count'] == 0
