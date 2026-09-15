import re

import pytest
from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient
from security.models import ActiveSession, LoginHistory, OTP, TrustedDevice


@pytest.fixture
def login_user(db, django_user_model, settings):
    from companies.models import Company
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.SECURE_SSL_REDIRECT = False
    cache.clear()
    company = Company.objects.create(name="Login regression")
    return django_user_model.objects.create_user(email="login@example.test", full_name="Login",
        password="correct-password-123", company=company, role="EMPLOYEE", is_active=True,
        email_verified=True, account_state="ACTIVE")


def challenge_for(client, user):
    response = client.post("/api/v1/auth/token/", {"email": user.email, "password": "correct-password-123"})
    assert response.status_code == 202
    assert response.data["otp_required"] is True
    assert response.data["expires_in"] == 300
    assert "access" not in response.data
    assert not ActiveSession.objects.filter(user=user).exists()
    fields = response.data
    challenge_id = fields["challenge_id"]
    if isinstance(challenge_id, list):
        challenge_id = challenge_id[0]
    code = re.search(r"\b\d{6}\b", mail.outbox[-1].body).group()
    return {"email": user.email, "challenge_id": str(challenge_id), "code": code}


def test_otp_trusted_device_and_refresh_rotation(login_user):
    client = APIClient()
    challenge = challenge_for(client, login_user)
    response = client.post("/api/v1/verify-otp/", {**challenge, "trust_device": True}, format="json")
    assert response.status_code == 200, response.data
    tokens = response.data
    assert LoginHistory.objects.filter(user=login_user, successful=True).count() == 1
    assert TrustedDevice.objects.get(user=login_user).token_hash != tokens["device_token"]
    assert client.post("/api/v1/verify-otp/", challenge).status_code == 400
    refreshed = client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]})
    assert refreshed.status_code == 200
    assert client.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}).status_code == 401
    assert client.post("/api/v1/auth/token/refresh/", {"refresh": refreshed.data["refresh"]}).status_code == 200
    trusted = client.post("/api/v1/auth/token/", {"email": login_user.email,
        "password": "correct-password-123", "device_token": tokens["device_token"]})
    assert trusted.status_code == 200
    assert len(mail.outbox) == 1


def test_wrong_otp_persists_attempts_and_invalid_challenge_does_not_crash(login_user):
    client = APIClient()
    challenge = challenge_for(client, login_user)
    wrong = "999999" if challenge["code"] != "999999" else "888888"
    assert client.post("/api/v1/verify-otp/", {**challenge, "code": wrong}).status_code == 400
    assert OTP.objects.get(user=login_user).attempts == 1
    assert client.post("/api/v1/verify-otp/", {**challenge, "challenge_id": "bad"}).status_code == 400


def test_disabled_account_cannot_refresh(login_user):
    client = APIClient()
    challenge = challenge_for(client, login_user)
    response = client.post("/api/v1/verify-otp/", challenge)
    login_user.is_active = False
    login_user.save(update_fields=["is_active"])
    assert client.post("/api/v1/auth/token/refresh/", {"refresh": response.data["refresh"]}).status_code == 400


def test_frontend_contract_and_trusted_header(login_user):
    client = APIClient()
    challenge = challenge_for(client, login_user)
    challenge.pop("email")
    verified = client.post("/api/v1/auth/verify-otp/", {**challenge, "trust_device": True}, format="json")
    assert verified.status_code == 200, verified.data
    token = verified.data["trusted_device_token"]
    assert token == verified.data["device_token"]
    assert verified.data["otp_required"] is False
    response = client.post("/api/v1/auth/token/", {"email": login_user.email, "password": "correct-password-123"}, HTTP_X_SMARTBIZ_DEVICE_TOKEN=token)
    assert response.status_code == 200
    assert "access" in response.data
    assert len(mail.outbox) == 1
    device = TrustedDevice.objects.get(user=login_user)
    device.is_active = False
    device.save(update_fields=["is_active"])
    response = client.post("/api/v1/auth/token/", {"email": login_user.email, "password": "correct-password-123"}, HTTP_X_SMARTBIZ_DEVICE_TOKEN=token)
    assert response.status_code == 202


def test_optional_email_must_match_challenge(login_user):
    client = APIClient()
    challenge = challenge_for(client, login_user)
    response = client.post("/api/v1/auth/verify-otp/", {**challenge, "email": "another@example.test"})
    assert response.status_code == 400
    assert not ActiveSession.objects.filter(user=login_user).exists()
    assert client.post("/api/v1/auth/verify-otp/", challenge).status_code == 200


def test_device_header_cors_preflight(settings):
    settings.SECURE_SSL_REDIRECT = False
    settings.CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]
    response = APIClient().options("/api/v1/auth/token/", HTTP_ORIGIN="http://localhost:5173", HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST", HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-smartbiz-device-token")
    assert response.status_code == 200
    assert "x-smartbiz-device-token" in response["Access-Control-Allow-Headers"]

@pytest.mark.parametrize('failure', [PermissionError(10013, 'blocked socket'), TimeoutError('timed out'), 0])
def test_email_failure_returns_safe_error_without_tokens(login_user, monkeypatch, failure):
    def unavailable(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr('users.serializers.send_mail', unavailable)
    response = APIClient().post('/api/v1/auth/token/', {
        'email': login_user.email, 'password': 'correct-password-123',
    })
    assert response.status_code == 503
    assert response.data['error']['code'] == 'VERIFICATION_EMAIL_UNAVAILABLE'
    assert 'access' not in response.data and 'refresh' not in response.data
    assert not ActiveSession.objects.filter(user=login_user).exists()
    assert OTP.objects.get(user=login_user).invalidated_at is not None
    assert 'blocked socket' not in str(response.data)
