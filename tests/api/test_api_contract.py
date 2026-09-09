import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_unauthenticated_error_has_stable_envelope():
    response = APIClient().get('/api/v1/dashboard/')
    assert response.status_code == 401
    assert 'error' in response.data
    assert {'code','message','request_id'} <= set(response.data['error'])

@pytest.mark.django_db
def test_request_id_is_echoed():
    response = APIClient().get('/api/v1/dashboard/', HTTP_X_REQUEST_ID='integration-test-123')
    assert response['X-Request-ID'] == 'integration-test-123'
