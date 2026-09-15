import pytest
from rest_framework.test import APIClient
from companies.models import Company, Branch
from subscriptions.models import Plan, Subscription
from security.models import AuditLog

@pytest.fixture
def setup(django_user_model):
    actor = django_user_model.objects.create_superuser(email='maintenance@example.test', full_name='Maintainer', password='test-password')
    company = Company.objects.create(name='Maintenance company')
    client = APIClient()
    client.force_authenticate(actor)
    return client, actor, company

@pytest.mark.django_db
def test_catalogue_denies_tenant_and_role_only_superuser(setup, django_user_model):
    client, actor, company = setup
    assert client.get('/api/platform/v1/administration/').status_code == 200
    for role in ['ADMIN', 'SUPERUSER']:
        user = django_user_model.objects.create_user(email=role+'@example.test', password='x', role=role, company=company)
        client.force_authenticate(user)
        assert client.get('/api/platform/v1/administration/').status_code == 403
        assert client.post('/api/platform/v1/administration/plans/', {}).status_code == 403

@pytest.mark.django_db
def test_create_edit_audit_reauthentication_and_stale_write(setup):
    client, actor, company = setup
    url = '/api/platform/v1/administration/plans/'
    values = dict(name='New plan', max_users=10, max_projects=10, max_branches=5, storage_limit_bytes=1000, price_monthly='25.50', is_active=True)
    body = {'values': values, 'password': 'incorrect', 'reason': 'Approved pricing'}
    assert client.post(url, body, format='json').status_code == 400
    body['password'] = 'test-password'
    body['reason'] = ' '
    assert client.post(url, body, format='json').status_code == 400
    body['reason'] = 'Approved pricing'
    response = client.post(url, body, format='json')
    assert response.status_code == 201, response.data
    row = response.data
    assert AuditLog.objects.filter(action='PLATFORM_RECORD_CREATED', object_id=row['id']).exists()
    assert 'test-password' not in str(list(AuditLog.objects.values()))
    detail = url + row['id'] + '/'
    update = {'values': {**row['values'], 'name': 'Updated'}, 'version': row['version'], 'password': 'test-password', 'reason': 'Rename'}
    response = client.put(detail, update, format='json')
    assert response.status_code == 200, response.data
    assert client.put(detail, update, format='json').status_code == 400

@pytest.mark.django_db
def test_no_secret_or_arbitrary_fields(setup):
    client, actor, company = setup
    response = client.get('/api/platform/v1/administration/users/')
    assert response.status_code == 200
    assert 'password' not in str(response.data)
    assert 'is_superuser' not in str(response.data)
    assert client.get('/api/platform/v1/administration/otp/').status_code == 404
    row = response.data['results'][0]
    response = client.put('/api/platform/v1/administration/users/'+row['id']+'/', {'values': {**row['values'], 'is_superuser': True}, 'version': row['version'], 'password': 'test-password', 'reason': 'Invalid grant'}, format='json')
    assert response.status_code == 400

@pytest.mark.django_db
def test_branch_rejects_foreign_manager(setup, django_user_model):
    client, actor, company = setup
    foreign = Company.objects.create(name='Foreign company')
    user = django_user_model.objects.create_user(email='foreign@example.test', company=foreign)
    response = client.post('/api/platform/v1/administration/branches/', {'values': {'company': company.pk, 'name': 'Branch', 'code': 'BR', 'manager': str(user.pk), 'location': '', 'is_active': True}, 'password': 'test-password', 'reason': 'Setup'}, format='json')
    assert response.status_code == 400, response.data
    assert not Branch.objects.exists()

@pytest.mark.django_db
def test_last_admin_cannot_be_demoted(setup, django_user_model):
    client, actor, company = setup
    user = django_user_model.objects.create_user(email='last@example.test', company=company, role='ADMIN', is_active=True, account_state='ACTIVE')
    url = f'/api/platform/v1/administration/users/{user.pk}/'
    row = client.get(url).data
    response = client.put(url, {'values': {**row['values'], 'role': 'EMPLOYEE'}, 'version': row['version'], 'password': 'test-password', 'reason': 'Demote'}, format='json')
    assert response.status_code == 400, response.data
    user.refresh_from_db()
    assert user.role == 'ADMIN'

@pytest.mark.django_db
def test_plan_cannot_shrink_below_usage(setup, django_user_model):
    client, actor, company = setup
    plan = Plan.objects.create(name='Capacity', max_users=10, max_projects=10, max_branches=10, price_monthly=10)
    Subscription.objects.create(company=company, plan=plan)
    django_user_model.objects.create_user(email='usage@example.test', company=company, is_active=True)
    url = f'/api/platform/v1/administration/plans/{plan.pk}/'
    row = client.get(url).data
    response = client.put(url, {'values': {**row['values'], 'max_users': 0}, 'version': row['version'], 'password': 'test-password', 'reason': 'Reduce capacity'}, format='json')
    assert response.status_code == 400, response.data
    plan.refresh_from_db()
    assert plan.max_users == 10

@pytest.mark.django_db
def test_all_schemas_render(setup):
    client, _, _ = setup
    for item in client.get('/api/platform/v1/administration/').data:
        response = client.get('/api/platform/v1/administration/'+item['key']+'/')
        assert response.status_code == 200, response.data
        assert response.data['fields']

@pytest.mark.django_db
def test_published_form_is_protected_and_malformed_ids_are_handled(setup):
    from forms_engine.models import FormTemplate
    client, actor, company = setup
    template = FormTemplate.objects.create(company=company, name='Published', code='PUB', lifecycle_status='PUBLISHED')
    url = f'/api/platform/v1/administration/form-templates/{template.pk}/'
    assert client.get(url).status_code == 404
    response = client.put(url, {'values': {'name':'Changed'}, 'password':'test-password','reason':'Edit'}, format='json')
    assert response.status_code == 404, response.data
    template.refresh_from_db()
    assert template.name == 'Published'
    assert client.get('/api/platform/v1/administration/users/not-a-uuid/').status_code == 404

@pytest.mark.django_db
def test_company_transfer_is_rejected(setup):
    from projects.models import Project
    client, actor, company = setup
    other = Company.objects.create(name='Transfer destination')
    project = Project.objects.create(company=company, name='Original')
    url = f'/api/platform/v1/administration/projects/{project.pk}/'
    row = client.get(url).data
    response = client.put(url, {'values': {**row['values'], 'company': other.pk}, 'version': row['version'], 'password': 'test-password', 'reason': 'Move'}, format='json')
    assert response.status_code == 400, response.data
    project.refresh_from_db()
    assert project.company_id == company.pk

@pytest.mark.django_db
def test_plan_preview_and_both_save_paths_agree(setup):
    client, actor, company = setup
    current = Plan.objects.create(name='Current capacity', max_users=10, max_projects=10, max_branches=5, price_monthly=10)
    small = Plan.objects.create(name='Small capacity', max_users=10, max_projects=10, max_branches=1, price_monthly=20)
    sub = Subscription.objects.create(company=company, plan=current)
    for index in range(3):
        Branch.objects.create(company=company, name=f'Branch {index}', code=f'B{index}')
    response = client.get(f'/api/platform/v1/subscriptions/{sub.pk}/plan-options/')
    assert response.status_code == 200
    option = next(item for item in response.data if item['id'] == small.pk)
    assert 'allows 1 branches' in option['issues'][0]
    assert '3 active branches' in option['issues'][0]
    response = client.post(f'/api/platform/v1/subscriptions/{sub.pk}/change-plan/', {'plan_id':small.pk,'reason':'Change plan'}, format='json')
    assert response.status_code == 400
    url = f'/api/platform/v1/administration/subscriptions/{sub.pk}/'
    row = client.get(url).data
    response = client.put(url, {'values': {**row['values'], 'plan': small.pk}, 'version':row['version'], 'password':'test-password','reason':'Change plan'}, format='json')
    assert response.status_code == 400
    sub.refresh_from_db()
    assert sub.plan_id == current.pk
    Branch.objects.filter(company=company).exclude(code='B0').update(is_active=False)
    response = client.post(f'/api/platform/v1/subscriptions/{sub.pk}/change-plan/', {'plan_id':small.pk,'reason':'Capacity now fits'}, format='json')
    assert response.status_code == 200, response.data
