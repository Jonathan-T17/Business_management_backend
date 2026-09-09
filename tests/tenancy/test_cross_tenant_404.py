import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_platform_identity_cannot_use_tenant_dashboard(django_user_model):
    platform = django_user_model.objects.create_user(
        email='platform@example.test', password='x', role='SUPERUSER',
        is_superuser=True, is_active=True,
    )
    client = APIClient(); client.force_authenticate(platform)
    response = client.get('/api/v1/dashboard/')
    assert response.status_code in (403, 404)
