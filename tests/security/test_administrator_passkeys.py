import base64
import hashlib
import json
import os
from datetime import timedelta
import pytest
import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from security.models import AdministratorPasskey, PasskeyChallenge, ActiveSession
from security.services import create_active_session

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures('passkey_configuration')]


@pytest.fixture
def passkey_configuration():
    with override_settings(DEBUG=True, WEBAUTHN_RP_ID='localhost', WEBAUTHN_ORIGINS=('http://localhost:3000',), CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache','LOCATION':os.urandom(8).hex()}}):
        yield


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_superuser(email='passkey-owner@example.test', full_name='Owner', password='test-password')


def client_for(user, fresh=True):
    refresh = RefreshToken.for_user(user)
    session = create_active_session(RequestFactory().get('/'), user, refresh['jti'], mfa_verified=True)
    if not fresh:
        session.mfa_verified_at = timezone.now()-timedelta(minutes=16)
        session.save(update_fields=('mfa_verified_at',))
    refresh['sid'] = str(session.pk)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, session


@pytest.fixture
def authenticator():
    return ec.generate_private_key(ec.SECP256R1()), os.urandom(32)


def proof(options, authenticator, user, register=False, origin='http://localhost:3000', uv=True, count=1, cross_origin=False):
    private, cred = authenticator
    client = json.dumps({'type':'webauthn.create' if register else 'webauthn.get', 'challenge':options['challenge'], 'origin':origin, 'crossOrigin':cross_origin}, separators=(',',':')).encode()
    flags = (0x41 if register else 0x01) | (0x04 if uv else 0)
    data = hashlib.sha256(b'localhost').digest()+bytes([flags])+(0 if register else count).to_bytes(4,'big')
    response = {'clientDataJSON':b64(client)}
    if register:
        numbers = private.public_key().public_numbers()
        cose = cbor2.dumps({1:2, 3:-7, -1:1, -2:numbers.x.to_bytes(32,'big'), -3:numbers.y.to_bytes(32,'big')})
        data += bytes(16)+len(cred).to_bytes(2,'big')+cred+cose
        response['attestationObject'] = b64(cbor2.dumps({'fmt':'none','authData':data,'attStmt':{}}))
    else:
        response.update(authenticatorData=b64(data), signature=b64(private.sign(data+hashlib.sha256(client).digest(),ec.ECDSA(hashes.SHA256()))), userHandle=b64(user.pk.bytes))
    return {'id':b64(cred),'rawId':b64(cred),'type':'public-key','response':response}


def enroll(owner, authenticator):
    client, session = client_for(owner)
    start = client.post('/api/v1/security/passkeys/register/options/', {'name':'Test key','password':'test-password'}, format='json')
    assert start.status_code == 200, start.data
    body = {'challenge_id':start.data['challenge_id'],'credential':proof(start.data['options'],authenticator,owner,register=True)}
    complete = client.post('/api/v1/security/passkeys/register/verify/', body, format='json')
    assert complete.status_code == 201, complete.data
    return client, session, complete.data['id'], body


def login_options(owner):
    client = APIClient()
    response = client.post('/api/v1/auth/passkey/options/', {'email':owner.email,'password':'test-password'}, format='json')
    assert response.status_code == 200, response.data
    return client, response.data


def test_real_registration_authentication_replay_and_revocation(owner, authenticator):
    manager, old_session, key_id, registration = enroll(owner, authenticator)
    assert manager.post('/api/v1/security/passkeys/register/verify/', registration, format='json').status_code == 400
    client, options = login_options(owner)
    body = {'challenge_id':options['challenge_id'],'credential':proof(options['options'],authenticator,owner)}
    login = client.post('/api/v1/auth/passkey/verify/', body, format='json')
    assert login.status_code == 200, login.data
    assert client.post('/api/v1/auth/passkey/verify/', body, format='json').status_code == 400
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    assert client.get('/api/platform/v1/security/summary/').status_code == 200
    key = AdministratorPasskey.objects.get(pk=key_id)
    assert key.sign_count == 1 and key.last_used_at
    assert manager.post(f'/api/v1/security/passkeys/{key_id}/revoke/', {'password':'wrong'}, format='json').status_code == 400
    revoked = manager.post(f'/api/v1/security/passkeys/{key_id}/revoke/', {'password':'test-password'}, format='json')
    assert revoked.status_code == 200
    assert client.get('/api/platform/v1/security/summary/').status_code == 401
    old_session.refresh_from_db()
    assert not old_session.is_active
    assert APIClient().post('/api/v1/auth/passkey/options/', {'email':owner.email,'password':'test-password'}, format='json').status_code == 400


@pytest.mark.parametrize('failure', ['origin','uv','challenge','signature','counter','password_changed','expired','foreign_handle','cross_origin'])
def test_signed_assertion_security_failures(owner, authenticator, failure):
    enroll(owner, authenticator)
    client, options = login_options(owner)
    credential = proof(options['options'],authenticator,owner,origin='https://evil.example' if failure=='origin' else 'http://localhost:3000',uv=failure!='uv',cross_origin=failure=='cross_origin')
    challenge = PasskeyChallenge.objects.get(pk=options['challenge_id'])
    if failure == 'challenge':
        challenge.challenge=b'wrong';challenge.save(update_fields=('challenge',))
    elif failure == 'signature':
        credential['response']['signature']=b64(b'bad')
    elif failure == 'counter':
        AdministratorPasskey.objects.filter(user=owner).update(sign_count=2)
    elif failure == 'password_changed':
        owner.set_password('changed-password');owner.save(update_fields=('password',))
    elif failure == 'expired':
        challenge.expires_at=timezone.now()-timedelta(seconds=1);challenge.save(update_fields=('expires_at',))
    elif failure == 'foreign_handle':
        credential['response']['userHandle']=b64(bytes(16))
    response = client.post('/api/v1/auth/passkey/verify/', {'challenge_id':challenge.pk,'credential':credential}, format='json')
    assert response.status_code == 400, response.data
    assert 'access' not in response.data
    assert ActiveSession.objects.filter(user=owner).count() == 1


@pytest.mark.parametrize('failure', ['origin','uv'])
def test_registration_requires_expected_origin_and_device_verification(owner, authenticator, failure):
    client, _ = client_for(owner)
    start = client.post('/api/v1/security/passkeys/register/options/', {'name':'Test','password':'test-password'}, format='json')
    response = client.post('/api/v1/security/passkeys/register/verify/', {'challenge_id':start.data['challenge_id'],'credential':proof(start.data['options'],authenticator,owner,register=True,origin='https://evil.example' if failure=='origin' else 'http://localhost:3000',uv=failure!='uv')},format='json')
    assert response.status_code == 400
    assert not AdministratorPasskey.objects.exists()


def test_recent_verification_ownership_and_operator_boundary(owner, authenticator, django_user_model):
    old, _ = client_for(owner, fresh=False)
    assert old.post('/api/v1/security/passkeys/register/options/', {'name':'Test','password':'test-password'}, format='json').status_code == 403
    client, _, key_id, _ = enroll(owner, authenticator)
    other = django_user_model.objects.create_superuser(email='passkey-other@example.test', full_name='Other', password='test-password')
    other.platform_duty='SUPPORT';other.save(update_fields=('platform_duty',))
    foreign, _ = client_for(other)
    assert foreign.get('/api/v1/security/passkeys/').data['passkeys'] == []
    assert foreign.post(f'/api/v1/security/passkeys/{key_id}/revoke/', {'password':'test-password'}, format='json').status_code == 404
    tenant = django_user_model.objects.create_user(email='passkey-tenant@example.test', password='test-password',is_active=True)
    client.force_authenticate(tenant)
    assert client.get('/api/v1/security/passkeys/').status_code == 403
    with override_settings(WEBAUTHN_ORIGINS=('https://evil.example',)):
        assert foreign.get('/api/v1/security/passkeys/').data['enabled'] is False


def test_failed_management_password_counts_and_invalid_proof_consumed(owner, authenticator):
    from security.models import FailedLoginAttempt
    client, _ = client_for(owner)
    response = client.post('/api/v1/security/passkeys/register/options/', {'name':'Test','password':'wrong'}, format='json')
    assert response.status_code == 400
    assert FailedLoginAttempt.objects.get().attempts == 1
    start = client.post('/api/v1/security/passkeys/register/options/', {'name':'Test','password':'test-password'}, format='json')
    assert start.status_code == 200
    malformed = {'id':'bad','rawId':None,'type':'public-key','response':{}}
    response = client.post('/api/v1/security/passkeys/register/verify/', {'challenge_id':start.data['challenge_id'],'credential':malformed}, format='json')
    assert response.status_code == 400
    assert PasskeyChallenge.objects.get(pk=start.data['challenge_id']).consumed_at is not None


def test_rp_and_http_deployment_configuration_is_checked(owner):
    client, _ = client_for(owner)
    with override_settings(DEBUG=False):
        assert client.get('/api/v1/security/passkeys/').data['enabled'] is False
    with override_settings(WEBAUTHN_RP_ID='localhost:3000'):
        assert client.get('/api/v1/security/passkeys/').data['enabled'] is False
    with override_settings(WEBAUTHN_RP_ID='app.example.com', WEBAUTHN_ORIGINS=('https://app.example.com',), DEBUG=False):
        assert client.get('/api/v1/security/passkeys/').data['enabled'] is True
