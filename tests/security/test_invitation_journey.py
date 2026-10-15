from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company, CompanyInvite
from organizations.models import EmployeeProfile, Position


@pytest.mark.django_db
def test_invitation_tracking_prioritizes_assignment_and_separates_history(django_user_model):
    company = Company.objects.create(name="Invitation journey")
    admin = django_user_model.objects.create_user(email="admin@journey.test", company=company, role="ADMIN", is_active=True)
    client = APIClient()
    client.force_authenticate(admin)
    expiration = timezone.now() + timedelta(days=3)

    def invitation(email, **values):
        return CompanyInvite.objects.create(company=company, email=email, role="EMPLOYEE", expires_at=expiration, **values)

    awaiting = invitation("awaiting@journey.test", status="ACCEPTED")
    pending = invitation("pending@journey.test", status="PENDING")
    expired = invitation("expired@journey.test", status="PENDING")
    expired.expires_at = timezone.now() - timedelta(seconds=1)
    expired.save(update_fields=["expires_at"])
    revoked = invitation("revoked@journey.test", status="REVOKED")
    assigned = invitation("assigned@journey.test", status="ACCEPTED")
    user = django_user_model.objects.create_user(email=assigned.email, company=company, role="EMPLOYEE", is_active=True)
    position = Position.objects.create(company=company, title="Operator")
    EmployeeProfile.objects.create(user=user, company=company, employee_id="01", position=position)
    foreign = Company.objects.create(name="Foreign invitations")
    CompanyInvite.objects.create(company=foreign, email="foreign@journey.test", role="EMPLOYEE", expires_at=expiration)
    base = "/api/v1/invites/"
    response = client.get(base, {"bucket": "active"})
    assert response.status_code == 200, response.data
    rows = response.data["results"]
    assert [row["id"] for row in rows] == [awaiting.pk, pending.pk]
    assert rows[0]["assignment_status"] == "AWAITING_POSITION"
    history = client.get(base, {"bucket": "history"}).data["results"]
    assert {row["id"] for row in history} == {assigned.pk, expired.pk, revoked.pk}
    assert client.get(base, {"bucket": "unknown"}).status_code == 400
    position.is_active = False
    position.save(update_fields=["is_active"])
    assert assigned.pk in {row["id"] for row in client.get(base, {"bucket": "active"}).data["results"]}
