import pytest
from core.capability_service import CapabilityService

@pytest.mark.django_db
def test_platform_superuser_does_not_inherit_compensation_capability(django_user_model):
    user = django_user_model.objects.create_user(
        email='platform-sensitive@example.test', password='x', role='SUPERUSER',
        is_superuser=True, is_active=True,
    )
    assert not CapabilityService.has(user, 'VIEW_COMPENSATION')

@pytest.mark.django_db
def test_company_admin_does_not_automatically_view_precise_location(django_user_model):
    from companies.models import Company
    company = Company.objects.create(name='Sensitive Tenant')
    user = django_user_model.objects.create_user(
        email='admin-sensitive@example.test', password='x', role='ADMIN',
        company=company, is_active=True,
    )
    assert not CapabilityService.has(user, 'VIEW_FIELD_LOCATION')
