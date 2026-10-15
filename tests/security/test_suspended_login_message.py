import pytest
from rest_framework.test import APIClient
from companies.models import Company
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolated_login_rate_bucket():
    # These tests check messages, not the independent rate-limit boundary.
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["ADMIN", "EMPLOYEE"])
def test_suspended_company_login_message_contract(django_user_model, settings, role):
    settings.SECURE_SSL_REDIRECT = False
    company = Company.objects.create(name=f"Synthetic suspended login {role}", is_active=False)
    user = django_user_model.objects.create_user(email=f"suspended-message-{role.lower()}@example.test",
        full_name="Synthetic login check", password="test-password", role=role, company=company,
        is_active=True, email_verified=True, account_state="ACTIVE")
    result = APIClient().post("/api/v1/auth/token/", {"email":user.email, "password":"test-password"}, format="json")
    assert result.status_code == 403, result.data
    assert result.data["error"]["message"] == "Your company workspace is suspended. Contact your company administrator or platform support."
    assert result.data["error"]["code"] == "ACCOUNT_ACCESS_UNAVAILABLE"
    assert "access" not in result.data and "refresh" not in result.data


@pytest.mark.django_db
@pytest.mark.parametrize("state,phrase", [("archived","workspace has been archived"),
    ("DEACTIVATED","account is deactivated"),("SUSPENDED","account is suspended"),
    ("TERMINATED","access to this company has ended"),("PENDING_VERIFICATION","Verify your email address")])
def test_login_explains_access_state_only_after_correct_password(django_user_model,settings,state,phrase):
    from django.utils import timezone
    settings.SECURE_SSL_REDIRECT=False
    company=Company.objects.create(name="Synthetic access message company",is_active=state!="archived",
        archived_at=timezone.now() if state=="archived" else None)
    user=django_user_model.objects.create_user(email="access-message@example.test",full_name="Synthetic message user",
        password="test-password",company=company,role="EMPLOYEE",is_active=state=="archived",
        email_verified=state!="PENDING_VERIFICATION",account_state="ACTIVE" if state=="archived" else state)
    client=APIClient()
    wrong=client.post("/api/v1/auth/token/",{"email":user.email,"password":"wrong-password"},format="json")
    unknown=client.post("/api/v1/auth/token/",{"email":"unknown-message@example.test","password":"wrong-password"},format="json")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.data["error"]["message"] == unknown.data["error"]["message"] == "Email or password is incorrect. Please try again."
    correct=client.post("/api/v1/auth/token/",{"email":user.email,"password":"test-password"},format="json")
    assert correct.status_code == 403,correct.data
    assert phrase in correct.data["error"]["message"]
    assert "access" not in correct.data and "refresh" not in correct.data
