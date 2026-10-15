import pytest
from rest_framework.test import APIClient
from companies.models import Company
from company_setup.models import FieldActivityTemplate


@pytest.mark.django_db
def test_field_configuration_rejects_unenforced_flags_and_preserves_legacy(django_user_model):
    company=Company.objects.create(name='Field config home')
    admin=django_user_model.objects.create_user(email='field-config@example.test',company=company,role='ADMIN')
    client=APIClient();client.force_authenticate(admin)
    endpoint='/api/v1/company-setup/field-templates/'
    for field in ('require_location','require_photo','require_signature','require_notes'):
        result=client.post(endpoint,{'name':field,'activity_type':'DELIVERY',field:True},format='json')
        assert result.status_code==400,result.data
        assert field in result.data['error']['fields']
    assert not FieldActivityTemplate.objects.filter(company=company).exists()
    created=client.post(endpoint,{'name':'Enforced form configuration','activity_type':'DELIVERY'},format='json')
    assert created.status_code==201,created.data
    legacy=FieldActivityTemplate.objects.create(company=company,name='Legacy evidence',activity_type='INSPECTION',require_photo=True)
    result=client.patch(f'{endpoint}{legacy.pk}/',{'name':'Reviewed legacy'},format='json')
    assert result.status_code==200 and result.data['require_photo'] is True
    result=client.patch(f'{endpoint}{legacy.pk}/',{'require_photo':False},format='json')
    assert result.status_code==200 and result.data['require_photo'] is False
