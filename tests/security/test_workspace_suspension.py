from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from companies.models import Company
from forms_engine.models import FormTemplate
from security.models import ActiveSession, AuditLog, SupportAccessSession


@pytest.fixture
def suspension_case(django_user_model, settings):
    settings.SECURE_SSL_REDIRECT=False
    settings.EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    company=Company.objects.create(name="Synthetic suspension workspace")
    other=Company.objects.create(name="Unaffected suspension workspace")
    owner=django_user_model.objects.create_superuser(email="suspension-owner@example.test",full_name="Owner",password="test-password")
    def member(email,company,role="EMPLOYEE",active=True):
        return django_user_model.objects.create_user(email=email,full_name=email,password="test-password",
            company=company,role=role,is_active=active,email_verified=True,account_state="ACTIVE" if active else "DEACTIVATED")
    admin=member("suspension-admin@example.test",company,"ADMIN")
    employee=member("suspension-employee@example.test",company)
    disabled=member("suspension-disabled@example.test",company,active=False)
    other_user=member("suspension-other@example.test",other)
    template=FormTemplate.objects.create(company=company,name="Preserved form",code="PRESERVE")
    return SimpleNamespace(company=company,other=other,owner=owner,admin=admin,employee=employee,
        disabled=disabled,other_user=other_user,template=template)


def signed_in(user, *, legacy=False):
    refresh=RefreshToken.for_user(user)
    session=ActiveSession.objects.create(user=user,company=None if legacy else user.company,
        ip_address="127.0.0.1",refresh_token_jti=refresh["jti"],expires_at=timezone.now()+timedelta(days=1))
    refresh["sid"]=str(session.pk)
    client=APIClient();client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client,session,str(refresh)


@pytest.mark.django_db
def test_suspend_and_reactivate_block_old_sessions_preserve_data_and_other_tenant(suspension_case):
    c=suspension_case; owner=APIClient();owner.force_authenticate(c.owner)
    employee,session,refresh=signed_in(c.employee)
    legacy,legacy_session,_=signed_in(c.admin,legacy=True)
    other,other_session,_=signed_in(c.other_user)
    grant=SupportAccessSession.objects.create(company=c.company,support_agent=c.owner,reason="Synthetic access",status="ACTIVE",expires_at=timezone.now()+timedelta(hours=1))
    assert employee.get("/api/v1/users/me/").status_code == 200
    assert legacy.get("/api/v1/users/me/").status_code == 200
    url=f"/api/platform/v1/companies/{c.company.pk}/"
    suspended=owner.post(url+"deactivate/",{"reason":"Investigating a reported incident"},format="json")
    assert suspended.status_code == 200 and suspended.data["is_active"] is False, suspended.data
    c.company.refresh_from_db();session.refresh_from_db();legacy_session.refresh_from_db();grant.refresh_from_db()
    assert not c.company.is_active and c.company.archived_at is None
    assert not session.is_active and not legacy_session.is_active and grant.status == "ENDED"
    assert employee.get("/api/v1/users/me/").status_code == 401
    assert legacy.get("/api/v1/users/me/").status_code == 401
    assert other.get("/api/v1/users/me/").status_code == 200
    other_session.refresh_from_db();assert other_session.is_active
    assert APIClient().post("/api/v1/auth/token/",{"email":c.employee.email,"password":"test-password"},format="json").status_code in (400,401,403)
    assert owner.post(url+"deactivate/",{"reason":"Repeated stale action"},format="json").status_code == 400
    assert owner.post(url+"reactivate/",{},format="json").status_code == 400
    reactivated=owner.post(url+"reactivate/",{"reason":"Investigation resolved"},format="json")
    assert reactivated.status_code == 200 and reactivated.data["is_active"] is True, reactivated.data
    c.company.refresh_from_db();c.disabled.refresh_from_db();session.refresh_from_db();grant.refresh_from_db()
    assert c.company.is_active and not c.disabled.is_active and c.disabled.account_state == "DEACTIVATED"
    assert not session.is_active and grant.status == "ENDED"
    assert employee.get("/api/v1/users/me/").status_code == 401
    assert APIClient().post("/api/v1/auth/token/refresh/",{"refresh":refresh},format="json").status_code in (400,401)
    c.employee.refresh_from_db()
    fresh,_,_=signed_in(c.employee)
    assert fresh.get("/api/v1/users/me/").status_code == 200
    assert FormTemplate.objects.filter(pk=c.template.pk,name="Preserved form").exists()
    assert AuditLog.objects.filter(company=c.company,action="WORKSPACE_SUSPENDED",description="Investigating a reported incident").exists()
    assert AuditLog.objects.filter(company=c.company,action="WORKSPACE_REACTIVATED",description="Investigation resolved").exists()


@pytest.mark.django_db
def test_suspension_and_session_revocation_roll_back_together_on_failure(suspension_case):
    c=suspension_case;client=APIClient();client.force_authenticate(c.owner)
    _,session,_=signed_in(c.employee)
    baseline=AuditLog.objects.count()
    with patch("companies.lifecycle.create_audit_log",side_effect=RuntimeError("Synthetic audit outage")),pytest.raises(RuntimeError):
        client.post(f"/api/platform/v1/companies/{c.company.pk}/deactivate/",{"reason":"Atomicity check"},format="json")
    c.company.refresh_from_db();session.refresh_from_db()
    assert c.company.is_active and session.is_active
    assert AuditLog.objects.count() == baseline


@pytest.mark.django_db
def test_suspend_reason_and_authority_are_validated(suspension_case):
    c=suspension_case;client=APIClient();url=f"/api/platform/v1/companies/{c.company.pk}/deactivate/"
    for actor in (c.admin,c.employee):
        client.force_authenticate(actor)
        assert client.post(url,{"reason":"Not allowed"},format="json").status_code == 403
    c.owner.platform_duty="SUPPORT";c.owner.save(update_fields=["platform_duty"])
    client.force_authenticate(c.owner)
    assert client.post(url,{"reason":"Not allowed"},format="json").status_code == 403
    c.owner.platform_duty="OWNER";c.owner.save(update_fields=["platform_duty"])
    for payload in ({},{"reason":"  "},{"reason":"x"*1001},{"reason":{"unexpected":"value"}}):
        result=client.post(url,payload,format="json")
        assert result.status_code == 400,result.data
    c.company.refresh_from_db();assert c.company.is_active
