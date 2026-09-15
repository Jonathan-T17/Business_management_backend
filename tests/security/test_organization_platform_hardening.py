import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from companies.models import Company
from organizations.models import EmployeeProfile
from organizations.serializers import EmployeeNoteSerializer
from security.models import ActiveSession


@pytest.mark.django_db
def test_organization_edit_requires_capability_and_keeps_company_scope(django_user_model):
    from organizations.models import Department, UserCapabilityGrant
    from core.capabilities import Capabilities
    company = Company.objects.create(name='Organization editing')
    other = Company.objects.create(name='Other organization')
    user = django_user_model.objects.create_user(email='editor@boundary.test', company=company, role='EMPLOYEE')
    other_user = django_user_model.objects.create_user(email='other-editor@boundary.test', company=other, role='ADMIN')
    foreign = Department.objects.create(company=other, name='Foreign', created_by=other_user)
    client = APIClient()
    client.force_authenticate(user)
    root = '/api/v1/organizations/departments/'
    assert client.post(root, {'name': 'Operations'}).status_code == 403
    UserCapabilityGrant.objects.create(company=company, user=user, capability=Capabilities.MANAGE_ORGANIZATION)
    response = client.post(root, {'name': 'Operations'})
    assert response.status_code == 201, response.data
    assert Department.objects.get(pk=response.data['id']).company_id == company.pk
    assert client.patch(f'{root}{foreign.pk}/', {'name': 'Changed'}).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('identity', ['role', 'django_flag', 'companyless'])
def test_organization_routes_reject_non_tenant_identities(django_user_model, identity):
    company = Company.objects.create(name='Organization boundary')
    user = django_user_model.objects.create_user(
        email=f'{identity}@boundary.test', company=None if identity == 'companyless' else company,
        role='SUPERUSER' if identity == 'role' else 'ADMIN',
        is_superuser=identity == 'django_flag', is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user)
    for resource in ('departments', 'teams', 'positions', 'employees', 'employee-transfers',
                     'employee-notes', 'employee-delegations', 'employee-compensations',
                     'capability-grants', 'position-capability-grants'):
        response = client.get(f'/api/v1/organizations/{resource}/')
        assert response.status_code == 403, (resource, response.status_code)


@pytest.mark.django_db
def test_employee_notes_reject_cross_company_and_platform_input(django_user_model):
    from types import SimpleNamespace
    from rest_framework.exceptions import ValidationError
    company = Company.objects.create(name='Notes tenant')
    other = Company.objects.create(name='Other notes tenant')
    owner = django_user_model.objects.create_user(email='notes@boundary.test', company=company)
    profile = EmployeeProfile.objects.create(user=owner, company=company, employee_id='EMP-1')
    actor = django_user_model.objects.create_user(email='actor@boundary.test', company=other, role='ADMIN')
    serializer = EmployeeNoteSerializer(context={'request': SimpleNamespace(user=actor)})
    with pytest.raises(ValidationError):
        serializer.validate_employee(profile)
    actor.company = company
    actor.role = 'SUPERUSER'
    with pytest.raises(ValidationError):
        serializer.validate_employee(profile)
    actor.role = 'ADMIN'
    assert serializer.validate_employee(profile) == profile


@pytest.mark.django_db
@pytest.mark.parametrize('all_sessions', [False, True])
def test_platform_session_termination_blacklists_tokens(django_user_model, all_sessions):
    company = Company.objects.create(name='Session boundary')
    actor = django_user_model.objects.create_user(email='platform@boundary.test', role='SUPERUSER', is_active=True)
    user = django_user_model.objects.create_user(email='session@boundary.test', company=company, is_active=True)
    tokens = [RefreshToken.for_user(user) for _ in range(2)]
    sessions = [ActiveSession.objects.create(user=user, company=company,
                refresh_token_jti=token['jti'], ip_address='127.0.0.1') for token in tokens]
    url = (f'/api/platform/v1/users/{user.pk}/terminate-sessions/' if all_sessions else
           f'/api/platform/v1/security/sessions/{sessions[0].pk}/terminate/')
    client = APIClient()
    client.force_authenticate(user)
    assert client.post(url, {'reason': 'Test revocation'}).status_code == 403
    client.force_authenticate(actor)
    assert client.post(url, {'reason': ' '}).status_code == 400
    assert not BlacklistedToken.objects.filter(token__jti=tokens[0]['jti']).exists()
    response = client.post(url, {'reason': 'Test revocation'})
    assert response.status_code == 200, response.data
    for index, session in enumerate(sessions):
        session.refresh_from_db()
        revoked = all_sessions or index == 0
        assert session.is_active is not revoked
        assert BlacklistedToken.objects.filter(token__jti=tokens[index]['jti']).exists() is revoked
        if revoked:
            assert session.terminated_by_id == actor.pk
            assert session.termination_reason == 'SECURITY'
            assert session.termination_note == 'Test revocation'
    if all_sessions:
        assert client.post(url, {'reason': 'Repeat'}).data['terminated_sessions'] == 0
