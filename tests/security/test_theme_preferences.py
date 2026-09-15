import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_personal_theme_isolation_and_validation(django_user_model, settings):
    settings.SECURE_SSL_REDIRECT = False
    first = django_user_model.objects.create_user(email="theme1@example.test", full_name="First", password="test-password")
    second = django_user_model.objects.create_user(email="theme2@example.test", full_name="Second", password="test-password")
    client = APIClient()
    assert client.patch("/api/v1/users/me/preferences/", {"theme_preference": "dark"}).status_code in (401, 403)
    client.force_authenticate(first)
    assert client.get("/api/v1/users/me/").data["theme_preference"] == "system"
    for value in ("dark", "light", "system"):
        response = client.patch("/api/v1/users/me/preferences/", {"theme_preference": value, "id": str(second.pk)}, format="json")
        assert response.status_code == 200, response.data
        first.refresh_from_db(); second.refresh_from_db()
        assert first.theme_preference == value
        assert second.theme_preference == "system"
    assert client.patch("/api/v1/users/me/preferences/", {"theme_preference": "invalid"}).status_code == 400
    assert client.patch("/api/v1/users/me/preferences/", {}).status_code == 400
