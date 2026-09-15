import pytest
from rest_framework.test import APIClient
from companies.models import Company
from requests_app.models import BusinessRequest
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities
from security.models import AuditLog

@pytest.mark.django_db
def test_request_cancel_close(django_user_model):
    company = Company.objects.create(name='Request lifecycle')
    user = django_user_model.objects.create_user(email='requester@test.example',company=company,role='EMPLOYEE')
    obj = BusinessRequest.objects.create(company=company,requester=user,title='Test',request_number='REQ-TEST',request_type='CUSTOM')
    client = APIClient(); client.force_authenticate(user)
    url = f'/api/v1/business-requests/{obj.pk}/'
    assert 'CANCEL' in client.get(url).data['allowed_actions']
    assert client.post(url+'cancel/').status_code == 400
    assert client.post(url+'cancel/',{'reason':'No longer needed'}).data['status'] == 'CANCELLED'
    assert client.post(url+'cancel/',{'reason':'Again'}).status_code == 403
    assert AuditLog.objects.filter(object_id=str(obj.pk),metadata__reason='No longer needed').exists()
    obj.status='SUBMITTED'; obj.save()
    assert client.post(url+'cancel/',{'reason':'No'}).status_code == 403
    obj.status='FULFILLED'; obj.save()
    assert client.post(url+'close/').status_code == 403
    UserCapabilityGrant.objects.create(company=company,user=user,capability=Capabilities.FULFILL_REQUESTS)
    obj.status='APPROVED'; obj.save()
    response = client.post(url+'fulfill/', {'note':'Delivered to requester'})
    assert response.status_code == 200, response.data
    assert response.data['status'] == 'FULFILLED'
    assert AuditLog.objects.filter(object_id=str(obj.pk),metadata__note='Delivered to requester').exists()
    assert client.post(url+'close/').data['status'] == 'CLOSED'
    assert client.get(url).data['allowed_actions'] == []
    other=Company.objects.create(name='Other request lifecycle')
    user.company=other; user.save()
    assert client.post(url+'close/').status_code == 404
