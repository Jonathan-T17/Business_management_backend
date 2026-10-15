from datetime import timedelta

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from companies.models import Company
from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from security.models import ActiveSession
from security.services import create_active_session, terminate_session
from security.utils import get_client_ip
from users.serializers import ActiveCompanyTokenRefreshSerializer


def bound_tokens(user):
    refresh = RefreshToken.for_user(user)
    session = create_active_session(RequestFactory().get('/'), user, refresh['jti'])
    refresh['sid'] = str(session.pk)
    return refresh, session


@pytest.fixture
def account(django_user_model):
    company = Company.objects.create(name='Session checks')
    return django_user_model.objects.create_user(email='session-check@example.test',
        company=company, role='ADMIN', is_active=True, email_verified=True, account_state='ACTIVE')


@pytest.mark.django_db
def test_revoked_access_denied_without_affecting_another_session(account):
    refresh, session = bound_tokens(account)
    other, _ = bound_tokens(account)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    assert client.get('/api/v1/users/me/').status_code == 200
    terminate_session(session=session, actor=account)
    assert client.get('/api/v1/users/me/').status_code == 401
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {other.access_token}')
    assert client.get('/api/v1/users/me/').status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('state', ['missing', 'malformed', 'foreign', 'expired'])
def test_unbound_or_invalid_session_access_denied(account, django_user_model, state):
    refresh, session = bound_tokens(account)
    access = refresh.access_token
    if state == 'missing':
        del access['sid']
    elif state == 'malformed':
        access['sid'] = 'bad-id'
    elif state == 'foreign':
        other = django_user_model.objects.create_user(email='other-session@example.test', company=account.company)
        _, foreign = bound_tokens(other)
        access['sid'] = str(foreign.pk)
    else:
        session.expires_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=['expires_at'])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    assert client.get('/api/v1/users/me/').status_code == 401


@pytest.mark.django_db
def test_legacy_refresh_upgrade_rotation_and_revocation(account):
    refresh, session = bound_tokens(account)
    del refresh['sid']
    data = ActiveCompanyTokenRefreshSerializer().validate({'refresh': str(refresh)})
    assert AccessToken(data['access'])['sid'] == str(session.pk)
    assert RefreshToken(data['refresh'])['sid'] == str(session.pk)
    assert BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists()
    terminate_session(session=session, actor=account)
    with pytest.raises(Exception):
        ActiveCompanyTokenRefreshSerializer().validate({'refresh': data['refresh']})


@pytest.mark.django_db
def test_logout_cannot_revoke_someone_elses_refresh(account, django_user_model):
    own, own_session = bound_tokens(account)
    other = django_user_model.objects.create_user(email='logout-other@example.test', company=account.company)
    foreign, foreign_session = bound_tokens(other)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {own.access_token}')
    assert client.post('/api/v1/logout/', {'refresh': str(foreign)}).status_code == 400
    foreign_session.refresh_from_db()
    assert foreign_session.is_active
    assert not BlacklistedToken.objects.filter(token__jti=foreign['jti']).exists()
    assert client.post('/api/v1/logout/', {'refresh': str(own)}).status_code == 205
    own_session.refresh_from_db()
    assert own_session.termination_reason == 'LOGOUT'
    assert client.get('/api/v1/users/me/').status_code == 401


@pytest.mark.django_db
def test_role_only_platform_account_has_no_privileged_capabilities(django_user_model):
    actor = django_user_model.objects.create_user(email='role-only@example.test', role='SUPERUSER', is_active=True)
    assert CapabilityService.is_platform_identity(actor)
    assert not CapabilityService.is_tenant_identity(actor)
    assert not CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN)
    client = APIClient()
    client.force_authenticate(actor)
    assert client.get('/api/platform/v1/dashboard/').status_code == 403
    actor.is_superuser = True
    actor.is_staff = True
    actor.save()
    assert CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN)
    actor.must_change_password = True
    actor.save()
    assert not CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN)


@pytest.mark.django_db
def test_platform_password_reset_revokes_access_and_protects_platform_targets(account, django_user_model):
    operator = django_user_model.objects.create_superuser(email='reset-operator@example.test', full_name='Operator', password='test-password')
    refresh, session = bound_tokens(account)
    client = APIClient()
    client.force_authenticate(operator)
    response = client.post(f'/api/platform/v1/users/{account.pk}/require-password-reset/', {'reason': 'Compromised session'})
    assert response.status_code == 200
    session.refresh_from_db()
    assert not session.is_active
    assert session.termination_reason == 'PASSWORD_RESET'
    client.force_authenticate(None)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    assert client.get('/api/v1/users/me/').status_code == 401
    operator.role = 'ADMIN'
    operator.save()
    client.credentials()
    client.force_authenticate(operator)
    assert client.post(f'/api/platform/v1/users/{operator.pk}/deactivate/', {'reason': 'Invalid tenant action'}).status_code == 400


@override_settings(TRUSTED_PROXY_NETWORKS=['10.0.0.0/24'])
@pytest.mark.parametrize('peer,forwarded,expected', [
    ('192.0.2.4', '198.51.100.7', '192.0.2.4'),
    ('10.0.0.2', '198.51.100.7, 10.0.0.3', '198.51.100.7'),
    ('10.0.0.2', '203.0.113.8, 198.51.100.7', '198.51.100.7'),
    ('10.0.0.2', 'bad-value', '10.0.0.2'),
])
def test_proxy_chain_trust(peer, forwarded, expected):
    request = RequestFactory().get('/', REMOTE_ADDR=peer, HTTP_X_FORWARDED_FOR=forwarded)
    assert get_client_ip(request) == expected
    from api.throttles import LoginRateThrottle
    assert LoginRateThrottle().get_ident(request) == expected
