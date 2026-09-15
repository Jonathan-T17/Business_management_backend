import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from companies.models import Company, CompanyInvite
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities
from subscriptions.models import Plan, Subscription
from subscriptions.services import SubscriptionCapacity

@pytest.mark.django_db
def test_import_commit_and_invitation(django_user_model, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    company = Company.objects.create(name='Import tenant')
    actor = django_user_model.objects.create_user(email='admin@import.test', company=company, role='ADMIN')
    plan = Plan.objects.create(name='Import plan', max_users=2, max_projects=5, price_monthly=0)
    Subscription.objects.create(company=company, plan=plan)
    client = APIClient(); client.force_authenticate(actor)
    url = '/api/v1/imports/employees/'
    assert client.get(url + '00000000-0000-0000-0000-000000000001/').status_code == 403
    UserCapabilityGrant.objects.create(company=company,user=actor,capability=Capabilities.IMPORT_EMPLOYEES)
    def upload(email, employee_id):
        return client.post(url, {'file': SimpleUploadedFile('employees.csv', f'email,first_name,last_name,employee_id\n{email},Test,Employee,{employee_id}\n'.encode())}, format='multipart')
    response = upload('employee@import.test', 'IMP-1')
    assert response.status_code == 200, response.data
    detail = url + str(response.data['id']) + '/'
    assert response.data['status'] == 'READY'
    assert client.get(detail).status_code == 200
    response = client.post(detail + 'commit/')
    assert response.status_code == 200, response.data
    employee = django_user_model.objects.get(email='employee@import.test')
    assert employee.role == 'EMPLOYEE' and not employee.is_active and not employee.has_usable_password()
    assert SubscriptionCapacity.usage(company)['users'] == 2
    assert client.post(detail + 'commit/').status_code == 400
    invite = CompanyInvite.objects.get(email=employee.email)
    anon = APIClient()
    response = anon.post('/api/v1/register/', {'email':employee.email,'full_name':'Test Employee','password':'Strong-Imported-Password-983!','invite':str(invite.token)})
    assert response.status_code == 201, response.data
    employee.refresh_from_db(); invite.refresh_from_db()
    assert employee.has_usable_password() and not employee.is_active
    assert invite.status == 'ACCEPTED'
    assert django_user_model.objects.filter(email=employee.email).count() == 1
    assert anon.post('/api/v1/register/', {'email':employee.email,'full_name':'Duplicate','password':'Strong-Imported-Password-983!','company_name':'Duplicate company'}).status_code == 400
    assert not Company.objects.filter(name='Duplicate company').exists()
    response = upload('second@import.test', 'IMP-2')
    assert client.post(url + str(response.data['id']) + '/commit/').status_code == 400
    assert not django_user_model.objects.filter(email='second@import.test').exists()
    invalid = upload('invalid-email', 'IMP-3')
    assert invalid.data['invalid_rows'] == 1
    assert client.post(url + str(invalid.data['id']) + '/commit/').status_code == 400
    plan.max_users = 4; plan.save()
    stale = upload('stale@import.test', 'IMP-4')
    django_user_model.objects.create_user(email='stale@import.test', company=company)
    assert client.post(url + str(stale.data['id']) + '/commit/').status_code == 400
    from django.utils import timezone
    from datetime import timedelta
    CompanyInvite.objects.create(company=company, email='pending@import.test', role='EMPLOYEE', created_by=actor, expires_at=timezone.now() + timedelta(days=2))
    pending = upload('pending@import.test', 'IMP-5')
    assert pending.data['invalid_rows'] == 1
    assert SubscriptionCapacity.usage(company)['users'] == 4
    company2 = Company.objects.create(name='Other import tenant')
    actor.company = company2; actor.save()
    UserCapabilityGrant.objects.create(company=company2,user=actor,capability=Capabilities.IMPORT_EMPLOYEES)
    assert client.get(detail).status_code == 404
