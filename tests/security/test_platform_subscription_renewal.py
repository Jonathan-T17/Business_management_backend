from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from companies.models import Company
from subscriptions.models import Plan, Subscription
from security.models import AuditLog


@pytest.mark.django_db
def test_renewal_requires_authority_password_reason_and_future_date(django_user_model):
    company = Company.objects.create(name="Renewal company")
    plan = Plan.objects.create(name="Renewal Starter", price_monthly=0, max_users=10, max_projects=10, max_branches=10)
    sub = Subscription.objects.create(company=company, plan=plan, is_active=False,
                                      expires_at=timezone.now() - timedelta(days=1))
    admin = django_user_model.objects.create_superuser(email="renewal@example.test", full_name="Renewal admin", password="test-password")
    tenant = django_user_model.objects.create_user(email="tenant-renewal@example.test", password="x", role="ADMIN", company=company)
    client = APIClient()
    url = f"/api/platform/v1/subscriptions/{sub.pk}/renew/"
    body = {"expires_at": (timezone.now() + timedelta(days=30)).isoformat(),
            "reason": "Approved renewal", "password": "test-password"}
    client.force_authenticate(tenant)
    assert client.post(url, body, format="json").status_code == 403
    client.force_authenticate(admin)
    for changes in ({"password": "wrong"}, {"reason": " "},
                    {"expires_at": (timezone.now() - timedelta(days=1)).isoformat()}):
        assert client.post(url, {**body, **changes}, format="json").status_code == 400
    sub.refresh_from_db()
    assert not sub.is_active
    result = client.post(url, body, format="json")
    assert result.status_code == 200, result.data
    assert result.data["is_valid"]
    sub.refresh_from_db()
    assert sub.plan_id == plan.pk
    assert sub.renewed_at is not None
    assert result.data["renewed_at"] is not None
    assert AuditLog.objects.filter(description="Subscription renewed and activated.").exists()
    assert client.post(url, {**body, "expires_at": None}, format="json").status_code == 200
    sub.refresh_from_db()
    assert sub.expires_at is None and sub.is_valid
    plan.is_active = False
    plan.save()
    assert client.post(url, body, format="json").status_code == 400
    plan.is_active = True
    plan.max_users = 0
    plan.save()
    assert client.post(url, body, format="json").status_code == 400
    plan.max_users = 10
    plan.save()
    advanced = f"/api/platform/v1/administration/subscriptions/{sub.pk}/"
    row = client.get(advanced).data
    values = {**row["values"], "is_active": True,
              "expires_at": (timezone.now() - timedelta(days=1)).isoformat()}
    payload = {"values": values, "version": row["version"],
               "reason": "Renew through advanced administration", "password": "test-password"}
    assert client.put(advanced, payload, format="json").status_code == 400
    values["expires_at"] = body["expires_at"]
    response = client.put(advanced, payload, format="json")
    assert response.status_code == 200, response.data
    sub.refresh_from_db()
    assert sub.is_valid
