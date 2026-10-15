import pytest
from rest_framework.test import APIClient

from companies.models import Branch, Company
from organizations.models import EmployeeProfile


@pytest.fixture
def directory(django_user_model):
    company = Company.objects.create(name="Directory search company")
    other_company = Company.objects.create(name="Other directory company")
    north = Branch.objects.create(company=company, name="North")
    south = Branch.objects.create(company=company, name="South")
    admin = django_user_model.objects.create_user(email="directory-admin@example.test", full_name="Admin", company=company, role="ADMIN", is_active=True)
    manager = django_user_model.objects.create_user(email="directory-manager@example.test", full_name="Manager", company=company, branch=north, role="MANAGER", is_active=True)

    def employee(name, email, code, tenant, branch=None):
        user = django_user_model.objects.create_user(email=email, full_name=name, company=tenant, branch=branch, role="EMPLOYEE", is_active=True)
        return EmployeeProfile.objects.create(user=user, company=tenant, branch=branch, employee_id=code)

    alice = employee("Alice North", "alice-directory@example.test", "DIR-101", company, north)
    bob = employee("Bob South", "bob-directory@example.test", "DIR-202", company, south)
    outsider = employee("Alice Outside", "alice-outside@example.test", "DIR-303", other_company)
    client = APIClient()
    client.force_authenticate(admin)
    return client, admin, manager, alice, bob, outsider


@pytest.mark.django_db
@pytest.mark.parametrize("term", ["alice north", "ALICE-DIRECTORY@EXAMPLE.TEST", "DIR-101"])
def test_search_matches_name_email_and_employee_id(directory, term):
    client, _, _, alice, _, _ = directory
    result = client.get("/api/v1/employees/", {"search": term})
    assert result.status_code == 200, result.data
    assert [row["id"] for row in result.data["results"]] == [alice.pk]


@pytest.mark.django_db
def test_no_matches_and_clearing_search_restore_results(directory):
    client, _, _, alice, bob, _ = directory
    empty = client.get("/api/v1/employees/", {"search": "not-a-real-directory-match"})
    assert empty.status_code == 200, empty.data
    assert empty.data["count"] == 0
    assert empty.data["results"] == []
    restored = client.get("/api/v1/employees/", {"search": ""})
    assert restored.status_code == 200, restored.data
    assert {row["id"] for row in restored.data["results"]} == {alice.pk, bob.pk}


@pytest.mark.django_db
def test_search_cannot_expand_company_branch_or_personal_visibility(directory):
    client, _, manager, alice, bob, _ = directory
    result = client.get("/api/v1/employees/", {"search": "Alice"})
    assert result.status_code == 200, result.data
    assert [row["id"] for row in result.data["results"]] == [alice.pk]
    client.force_authenticate(manager)
    result = client.get("/api/v1/employees/", {"search": bob.employee_id})
    assert result.status_code == 200, result.data
    assert result.data["count"] == 0
    client.force_authenticate(alice.user)
    result = client.get("/api/v1/employees/", {"search": bob.employee_id})
    assert result.status_code == 200, result.data
    assert result.data["count"] == 0


@pytest.mark.django_db
def test_search_filters_before_pagination(directory):
    client, _, _, alice, _, _ = directory
    result = client.get("/api/v1/organizations/employees/", {"search": "DIR", "page_size": 1})
    assert result.status_code == 200, result.data
    assert result.data["count"] == 2
    assert result.data["next"]
    assert [row["id"] for row in result.data["results"]] == [alice.pk]
