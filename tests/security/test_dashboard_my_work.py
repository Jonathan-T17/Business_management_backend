import pytest
from rest_framework.test import APIClient
from companies.models import Company
from forms_engine.models import FormTemplate, FormSubmission
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities


@pytest.mark.django_db
def test_personal_dashboard_counts_only_own_tenant_entries(django_user_model):
    company = Company.objects.create(name='Dashboard company')
    other = Company.objects.create(name='Other dashboard company')
    user = django_user_model.objects.create_user(email='dashboard@example.test', company=company, role='EMPLOYEE')
    peer = django_user_model.objects.create_user(email='dashboard-peer@example.test', company=company, role='EMPLOYEE')
    outsider = django_user_model.objects.create_user(email='dashboard-other@example.test', company=other, role='EMPLOYEE')
    template = FormTemplate.objects.create(company=company, name='Daily work', code='dashboard-work')
    foreign = FormTemplate.objects.create(company=other, name='Other work', code='dashboard-work')
    own = FormSubmission.objects.create(company=company, template=template, submitted_by=user, reference_number='OWN', status='DRAFT', data={'secret': 'never return answers'})
    FormSubmission.objects.create(company=company, template=template, submitted_by=peer, reference_number='PEER', status='APPROVED')
    FormSubmission.objects.create(company=other, template=foreign, submitted_by=outsider, reference_number='OTHER', status='APPROVED')
    client = APIClient()
    url = '/api/v1/form-submissions/my-work/'
    assert client.get(url).status_code in (401, 403)
    client.force_authenticate(user)
    assert client.get(url).status_code == 403
    UserCapabilityGrant.objects.create(company=company, user=user, capability=Capabilities.USE_FORMS)
    response = client.get(url)
    assert response.status_code == 200, response.data
    assert response.data['counts']['DRAFT'] == 1
    assert response.data['counts']['APPROVED'] == 0
    assert [row['id'] for row in response.data['recent']] == [str(own.pk)]
    assert set(response.data['recent'][0]) == {'id', 'name', 'status', 'updated_at'}
    for index in range(6):
        FormSubmission.objects.create(company=company, template=template, submitted_by=user, reference_number=f'RETURNED-{index}', status='RETURNED')
    response = client.get(url)
    assert response.data['counts']['RETURNED'] == 6
    assert len(response.data['recent']) == 5
    assert all(row['status'] == 'RETURNED' for row in response.data['recent'])
