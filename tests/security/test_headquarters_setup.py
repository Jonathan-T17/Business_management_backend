import pytest
from rest_framework.test import APIClient

from companies.models import Branch, Company
from company_setup.models import CompanySetupState
from company_setup.readiness import SetupReadinessService
from company_setup.setup_contract import SETUP_VERSION
from organizations.models import Position


@pytest.fixture
def office_client(django_user_model):
    company = Company.objects.create(name="Office structure", official_name="Office structure", country="RW")
    admin = django_user_model.objects.create_user(
        email="offices@example.test", company=company, role="ADMIN", is_active=True, account_state="ACTIVE",
    )
    client = APIClient()
    client.force_authenticate(admin)
    return company, admin, client


@pytest.mark.django_db
def test_designating_headquarters_preserves_structure_and_enforces_one(office_client):
    company, _, client = office_client
    first = Branch.objects.create(company=company, name="Main office")
    second = Branch.objects.create(company=company, name="Regional office")
    position = Position.objects.create(company=company, title="Operations", branch=first)
    endpoint = "/api/v1/company-setup/headquarters/"
    assert client.get(endpoint).data == {"headquarters": None}
    for branch in (first, first, second):
        result = client.put(endpoint, {"branch_id": branch.pk}, format="json")
        assert result.status_code == 200, result.data
        assert result.data["headquarters"]["id"] == branch.pk
        assert result.data["headquarters"]["is_headquarters"] is True
    company.refresh_from_db()
    position.refresh_from_db()
    assert company.headquarters_id == second.pk
    assert position.branch_id == first.pk
    assert company.branches.count() == 2
    listed = client.get("/api/v1/branches/").data
    rows = listed["results"] if isinstance(listed, dict) else listed
    assert [r["id"] for r in rows if r["is_headquarters"]] == [second.pk]


@pytest.mark.django_db
def test_headquarters_rejects_foreign_inactive_and_unauthorized_choices(office_client):
    company, admin, client = office_client
    inactive = Branch.objects.create(company=company, name="Closed", is_active=False)
    foreign = Branch.objects.create(company=Company.objects.create(name="Other"), name="Foreign office")
    endpoint = "/api/v1/company-setup/headquarters/"
    for branch in (inactive, foreign):
        assert client.put(endpoint, {"branch_id": branch.pk}, format="json").status_code == 400
    for payload in ({}, {"name": " "}, {"branch_id": 0}, {"branch_id": inactive.pk, "name": "Mixed"}):
        assert client.put(endpoint, payload, format="json").status_code == 400
    company.refresh_from_db()
    assert company.headquarters_id is None
    admin.role = "EMPLOYEE"
    admin.save(update_fields=["role"])
    assert client.put(endpoint, {"name": "New office"}, format="json").status_code == 403
    assert client.get(endpoint).status_code == 403


@pytest.mark.django_db
def test_headquarters_cannot_be_deactivated_or_deleted(office_client):
    company, _, client = office_client
    branch = Branch.objects.create(company=company, name="Main office")
    assert client.put("/api/v1/company-setup/headquarters/", {"branch_id": branch.pk}).status_code == 200
    endpoint = f"/api/v1/branches/{branch.pk}/"
    assert client.patch(endpoint, {"is_active": False}, format="json").status_code == 400
    assert client.post(endpoint + "deactivate/", {"reason": "Closing"}, format="json").status_code == 400
    assert client.delete(endpoint).status_code == 400
    branch.refresh_from_db()
    assert branch.is_active
    # General company edits cannot bypass headquarters validation.
    assert client.patch(f"/api/v1/company/{company.pk}/", {"headquarters": None}, format="json").status_code == 200
    company.refresh_from_db()
    assert company.headquarters_id == branch.pk


@pytest.mark.django_db
def test_new_headquarters_is_atomic_and_counts_as_only_required_location(office_client, monkeypatch):
    from subscriptions.services import SubscriptionService
    company, _, client = office_client
    monkeypatch.setattr(SubscriptionService, "can_add_branch", lambda company: True)
    endpoint = "/api/v1/company-setup/headquarters/"
    response = client.put(endpoint, {"name": "Head office", "location": "Kigali"}, format="json")
    assert response.status_code == 200, response.data
    assert client.put(endpoint, {"name": "Head office"}, format="json").status_code == 400
    company.refresh_from_db()
    assert company.branches.count() == 1
    assert "organization" in SetupReadinessService.configured_steps(company)
    monkeypatch.setattr(SubscriptionService, "can_add_branch", lambda company: False)
    assert client.put(endpoint, {"name": "Another office"}, format="json").status_code == 400
    assert company.branches.count() == 1


@pytest.mark.django_db
def test_existing_setup_resumes_at_headquarters_and_steps_are_sequential(office_client):
    company, _, client = office_client
    CompanySetupState.objects.create(company=company, onboarding_completed=True, setup_version=2,
        completed_steps=["v2:organization", "v2:departments", "v2:positions", "v2:permissions", "v2:employees"])
    Branch.objects.create(company=company, name="Headquarters")  # Names never choose authority.
    response = client.get("/api/v1/company-setup/status/").data
    assert SETUP_VERSION > 2
    assert not response["onboarding_completed"]
    assert response["current_step"] == "organization"
    assert client.get("/api/v1/company-setup/access/").data["setup_required"]
    result = client.post("/api/v1/company-setup/steps/complete/", {"step": "employees"})
    assert result.status_code == 400
    assert "headquarters" in str(result.data).lower()
