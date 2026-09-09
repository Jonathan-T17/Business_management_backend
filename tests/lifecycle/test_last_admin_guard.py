import pytest
from rest_framework.exceptions import ValidationError

@pytest.mark.django_db
def test_last_active_company_admin_cannot_be_deactivated(django_user_model):
    from companies.models import Company
    from users.services import TenantUserLifecycleService
    company = Company.objects.create(name='Admin Guard')
    admin = django_user_model.objects.create_user(
        email='only-admin@example.test', password='x', role='ADMIN', company=company, is_active=True,
    )
    with pytest.raises(ValidationError):
        TenantUserLifecycleService.deactivate(actor=admin, target=admin, reason='blocked')
