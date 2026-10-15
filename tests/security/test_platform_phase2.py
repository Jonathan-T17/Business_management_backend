from datetime import timedelta
import re
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from core.capability_service import CapabilityService
from core.capabilities import Capabilities as C
from core.admin_site import RecoveryAdminSite
from core.recovery_mfa import RecoveryMFAForm
from platform_admin.health import get_platform_health, record_reporting_run
from security.models import ActiveSession, TrustedDevice
from security.services import trusted_device_hash


@pytest.fixture
def operator(django_user_model):
    return django_user_model.objects.create_superuser(email='phase2-owner@example.test', full_name='Owner', password='test-password')


@pytest.mark.django_db
@pytest.mark.parametrize('duty,allowed,denied', [
    ('SECURITY', '/api/platform/v1/security/summary/', '/api/platform/v1/subscriptions/'),
    ('SUPPORT', '/api/platform/v1/support/tickets/', '/api/platform/v1/security/summary/'),
    ('SUBSCRIPTIONS', '/api/platform/v1/subscriptions/', '/api/platform/v1/security/sessions/'),
    ('AUDITOR', '/api/platform/v1/audit/', '/api/platform/v1/users/'),
])
def test_duties_separate_access(operator, duty, allowed, denied):
    operator.platform_duty = duty
    operator.save(update_fields=['platform_duty'])
    client = APIClient()
    client.force_authenticate(operator)
    assert client.get(allowed).status_code == 200
    assert client.get(denied).status_code == 403
    assert client.get('/api/platform/v1/administration/').status_code == 403
    assert not CapabilityService.has(operator, C.USE_FORMS)


@pytest.mark.django_db
def test_incident_password_transitions_history_and_auditor_denial(operator):
    operator.platform_duty = 'SECURITY'
    operator.save(update_fields=['platform_duty'])
    client = APIClient()
    client.force_authenticate(operator)
    root = '/api/platform/v1/security/incidents/'
    assert client.post(root, {'title':'Test incident', 'note':'Test evidence', 'password':'wrong'}, format='json').status_code == 400
    created = client.post(root, {'title':'Test incident', 'note':'Test evidence', 'password':'test-password'}, format='json')
    assert created.status_code == 201, created.data
    values = {'status':'INVESTIGATING', 'note':'Reviewed sign-ins', 'password':'test-password', 'updated_at':created.data['updated_at']}
    url = root+created.data['id']+'/transition/'
    response = client.post(url, values, format='json')
    assert response.status_code == 200, response.data
    assert len(response.data['events']) == 2
    assert client.post(url, values, format='json').status_code == 400
    values.update(status='RESOLVED', updated_at=response.data['updated_at'], note='Test resolved')
    resolved = client.post(url, values, format='json')
    assert resolved.status_code == 200
    assert resolved.data['resolved_at']
    operator.platform_duty = 'AUDITOR'
    operator.save(update_fields=['platform_duty'])
    assert client.get(root).status_code == 200
    assert client.post(root, {'title':'Denied','note':'Denied','password':'test-password'}, format='json').status_code == 403
    assert client.delete(root+created.data['id']+'/').status_code in (403,405)


@pytest.mark.django_db
def test_duty_changes_require_owner_password_keep_last_owner_and_revoke(operator, django_user_model):
    client = APIClient()
    client.force_authenticate(operator)
    url = '/api/platform/v1/security/access/'
    body = {'user_id':str(operator.pk),'duty':'SECURITY','expected_duty':'OWNER','reason':'Test separation','password':'test-password'}
    assert client.post(url, body, format='json').status_code == 400
    other = django_user_model.objects.create_superuser(email='phase2-other@example.test', full_name='Other', password='test-password')
    session = ActiveSession.objects.create(user=other, ip_address='127.0.0.1', refresh_token_jti='test-duty-session', expires_at=timezone.now()+timedelta(days=1))
    body['user_id'] = str(other.pk)
    body['password'] = 'incorrect'
    assert client.post(url, body, format='json').status_code == 400
    body['password'] = 'test-password'
    assert client.post(url, body, format='json').status_code == 200
    session.refresh_from_db()
    assert not session.is_active
    other.refresh_from_db()
    client.force_authenticate(other)
    assert client.get(url).status_code == 403
    assert client.post(url, body, format='json').status_code == 403


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_platform_trusted_device_still_requires_fresh_code(operator):
    TrustedDevice.objects.create(user=operator, token_hash=trusted_device_hash('known-device'))
    client = APIClient()
    response = client.post('/api/v1/auth/token/', {'email':operator.email,'password':'test-password','device_token':'known-device'}, format='json')
    assert response.status_code == 202, response.data
    assert response.data['otp_required']
    assert len(mail.outbox) == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_recovery_requires_code_consumes_it_and_expires(operator):
    request = RequestFactory().post('/internal/admin/login/')
    request.session = {}
    values = {'username':operator.email, 'password':'test-password'}
    form = RecoveryMFAForm(request=request, data=values)
    assert not form.is_valid()
    assert len(mail.outbox) == 1
    challenge = form.data['challenge_id']
    code = re.search(r'\b\d{6}\b', mail.outbox[0].body).group()
    values.update(challenge_id=challenge, verification_code=code)
    verified = RecoveryMFAForm(request=request, data=values)
    assert verified.is_valid(), verified.errors
    request.user = operator
    assert RecoveryAdminSite().has_permission(request)
    assert not RecoveryMFAForm(request=request, data=values).is_valid()
    request.session['platform_mfa_at'] = (timezone.now()-timedelta(minutes=16)).timestamp()
    assert not RecoveryAdminSite().has_permission(request)


@pytest.mark.django_db
def test_health_distinguishes_missing_failed_and_recent_evidence():
    from platform_admin.models import ServiceHealthEvidence
    cache.delete('platform.reporting.last_run')
    with patch('platform_admin.health.check_database', return_value={'status':'healthy'}), patch('platform_admin.health.check_cache', return_value={'status':'healthy'}):
        initial = get_platform_health()
        assert initial['status'] == 'partially_monitored'
        assert initial['services']['backups']['status'] == 'not_monitored'
        record_reporting_run('FAILED')
        assert get_platform_health()['status'] == 'degraded'
        record_reporting_run('SUCCESS')
        assert get_platform_health()['services']['reporting']['status'] == 'healthy'
        ServiceHealthEvidence.objects.filter(service='reporting').update(checked_at=timezone.now()-timedelta(minutes=4))
        assert get_platform_health()['services']['reporting']['status'] == 'unhealthy'
    cache.delete('platform.reporting.last_run')


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_platform_bearer_requires_verified_session_and_otp_binds_it(operator):
    from rest_framework_simplejwt.tokens import RefreshToken
    from security.services import create_active_session
    refresh = RefreshToken.for_user(operator)
    session = create_active_session(RequestFactory().get('/'), operator, refresh['jti'])
    refresh['sid'] = str(session.pk)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    assert client.get('/api/v1/users/me/').status_code == 401
    client.credentials()
    denied = client.post('/api/v1/auth/token/refresh/', {'refresh':str(refresh)}, format='json')
    assert denied.status_code == 400
    assert 'email verification code' in str(denied.data)
    challenge = client.post('/api/v1/auth/token/', {'email':operator.email,'password':'test-password'}, format='json')
    assert challenge.status_code == 202
    code = re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()
    verified = client.post('/api/v1/auth/verify-otp/', {'challenge_id':challenge.data['challenge_id'],'code':code}, format='json')
    assert verified.status_code == 200, verified.data
    token = verified.data['access']
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    assert client.get('/api/v1/users/me/').status_code == 200
    assert ActiveSession.objects.filter(user=operator, mfa_verified_at__isnull=False).exists()


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_recovery_login_template_and_session_proof(operator):
    from django.test import Client
    client = Client()
    first = client.post('/internal/admin/login/', {'username':operator.email,'password':'test-password'})
    assert first.status_code == 200
    assert b'name="verification_code"' in first.content
    challenge = re.search(rb'name="challenge_id" value="([^"]+)"', first.content).group(1).decode()
    code = re.search(r'\b\d{6}\b', mail.outbox[-1].body).group()
    second = client.post('/internal/admin/login/', {'username':operator.email,'password':'test-password','challenge_id':challenge,'verification_code':code,'next':'/internal/admin/'})
    assert second.status_code == 302
    assert client.session['platform_mfa_user'] == str(operator.pk)
    assert client.get('/internal/admin/').status_code == 200


def test_recovery_security_records_cannot_be_edited():
    from security.admin import ReadOnlySecurityAdmin
    assert not ReadOnlySecurityAdmin.has_add_permission(None, None)
    assert not ReadOnlySecurityAdmin.has_change_permission(None, None)
    assert not ReadOnlySecurityAdmin.has_delete_permission(None, None)
