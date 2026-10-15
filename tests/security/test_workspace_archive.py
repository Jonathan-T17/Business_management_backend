from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from core.authorization import Authorization
from security.models import ActiveSession, AuditLog, SupportAccessSession


@pytest.fixture
def workspace(django_user_model):
    company = Company.objects.create(name="Archive test workspace")
    admin = django_user_model.objects.create_user(email="archive-admin@example.test", password="test-password", full_name="Admin", role="ADMIN", company=company, is_active=True, email_verified=True, account_state="ACTIVE")
    employee = django_user_model.objects.create_user(email="archive-employee@example.test", password="test-password", full_name="Employee", role="EMPLOYEE", company=company, is_active=True, email_verified=True, account_state="ACTIVE")
    owner = django_user_model.objects.create_superuser(email="archive-owner@example.test", password="test-password", full_name="Owner")
    return SimpleNamespace(company=company, admin=admin, employee=employee, owner=owner)


def confirmation(company, **changes):
    return {"company_name": company.name, "reason": "Test archive lifecycle", "password": "test-password", **changes}


@pytest.mark.django_db
def test_archive_hides_workspace_revokes_access_and_only_owner_restores(workspace):
    w = workspace
    session = ActiveSession.objects.create(user=w.employee, company=w.company, ip_address="127.0.0.1", refresh_token_jti="archive-session", expires_at=timezone.now()+timedelta(days=1))
    grant = SupportAccessSession.objects.create(company=w.company, support_agent=w.owner, reason="Test grant", status="ACTIVE", expires_at=timezone.now()+timedelta(hours=1))
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(w.employee)
    token["sid"] = str(session.pk)
    access = str(token.access_token)
    authenticated = APIClient()
    authenticated.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert authenticated.get("/api/v1/users/me/").status_code == 200
    client = APIClient()
    client.force_authenticate(w.admin)
    url = f"/api/v1/company/{w.company.pk}/"
    result = client.post(url+"archive/", confirmation(w.company), format="json")
    assert result.status_code == 200, result.data
    w.company.refresh_from_db(); session.refresh_from_db(); grant.refresh_from_db()
    assert not w.company.is_active and w.company.archived_at
    assert timedelta(days=29) < w.company.recovery_until-timezone.now() <= timedelta(days=30)
    assert not session.is_active and grant.status == "ENDED"
    w.employee.refresh_from_db()
    assert not Authorization.can_authenticate(w.employee)
    assert authenticated.get("/api/v1/users/me/").status_code == 401
    assert client.get(url).status_code in (403, 404)
    assert client.post(url+"activate/", {}, format="json").status_code == 404
    platform_url = f"/api/platform/v1/companies/{w.company.pk}/"
    assert client.post(platform_url+"restore/", confirmation(w.company), format="json").status_code == 403
    client.force_authenticate(w.owner)
    listed = client.get("/api/platform/v1/companies/").data
    assert not any(row["id"] == w.company.pk for row in (listed.get("results", []) if isinstance(listed, dict) else listed))
    archived = client.get("/api/platform/v1/companies/?status=archived").data
    assert any(row["id"] == w.company.pk for row in (archived.get("results", []) if isinstance(archived, dict) else archived))
    assert client.post(platform_url+"reactivate/", {"reason":"Bypass"}, format="json").status_code == 400
    result = client.post(platform_url+"restore/", confirmation(w.company), format="json")
    assert result.status_code == 200, result.data
    w.company.refresh_from_db(); session.refresh_from_db(); grant.refresh_from_db()
    assert w.company.is_active and w.company.archived_at is None
    assert not session.is_active and grant.status == "ENDED"
    assert authenticated.get("/api/v1/users/me/").status_code == 401
    assert AuditLog.objects.filter(company=w.company, action="WORKSPACE_ARCHIVED").exists()
    assert AuditLog.objects.filter(company=w.company, action="WORKSPACE_RESTORED").exists()


@pytest.mark.django_db
def test_archive_confirmation_roles_and_database_guard(workspace):
    w = workspace; client = APIClient(); url=f"/api/v1/company/{w.company.pk}/archive/"
    client.force_authenticate(w.employee)
    assert client.post(url, confirmation(w.company), format="json").status_code == 403
    client.force_authenticate(w.admin)
    for changes in ({"password":"wrong"}, {"company_name":"wrong"}, {"reason":""}):
        assert client.post(url, confirmation(w.company, **changes), format="json").status_code == 400
    w.company.refresh_from_db(); assert w.company.archived_at is None
    other = Company.objects.create(name="Another archive workspace")
    assert client.post(f"/api/v1/company/{other.pk}/archive/", confirmation(other), format="json").status_code == 404
    with pytest.raises(IntegrityError), transaction.atomic():
        Company.objects.filter(pk=w.company.pk).update(archived_at=timezone.now(), is_active=True)


@pytest.mark.django_db
def test_recovery_keeps_employee_restrictions_and_previous_suspension(workspace):
    w=workspace; client=APIClient(); client.force_authenticate(w.owner)
    url=f"/api/platform/v1/companies/{w.company.pk}/"
    w.company.is_active=False; w.company.save(update_fields=["is_active"])
    w.employee.is_active=False; w.employee.account_state="DEACTIVATED"; w.employee.save(update_fields=["is_active", "account_state"])
    assert client.post(url+"archive/", confirmation(w.company), format="json").status_code == 200
    assert client.post(url+"restore/", confirmation(w.company), format="json").status_code == 200
    w.company.refresh_from_db(); w.employee.refresh_from_db()
    assert not w.company.is_active and not w.employee.is_active and w.employee.account_state == "DEACTIVATED"
    assert client.post(url+"archive/", confirmation(w.company), format="json").status_code == 200
    Company.objects.filter(pk=w.company.pk).update(recovery_until=timezone.now()-timedelta(seconds=1))
    assert client.post(url+"restore/", confirmation(w.company), format="json").status_code == 400
    w.owner.platform_duty="SUPPORT"; w.owner.save(update_fields=["platform_duty"])
    assert client.get("/api/platform/v1/companies/?status=archived").status_code == 403
