import pytest
from rest_framework.test import APIClient

from companies.models import Company


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,superuser,expected",
    [("ADMIN", False, "TENANT"), ("SUPERUSER", False, "PLATFORM"), ("ADMIN", True, "PLATFORM")],
)
def test_profile_context_matches_dashboard_boundary(django_user_model, role, superuser, expected):
    company = Company.objects.create(name="Dashboard identity")
    user = django_user_model.objects.create_user(
        email="dashboard@example.test", password="test-password",
        company=company, role=role, is_superuser=superuser,
    )
    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/v1/users/me/")
    assert response.status_code == 200, response.data
    assert response.data["context"] == expected
    if expected == "PLATFORM":
        assert client.get("/api/v1/dashboard/").status_code == 403
