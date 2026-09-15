from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from companies.models import Company
from field_operations.models import FieldActivity, FieldStop
from field_operations.serializers import FieldActivitySerializer, FieldStopSerializer


@pytest.fixture
def field_context(db, django_user_model, settings):
    settings.SECURE_SSL_REDIRECT = False
    company = Company.objects.create(name="Field company")
    other = Company.objects.create(name="Other field company")
    worker = django_user_model.objects.create_user(email="worker@field.test", company=company, role="EMPLOYEE", is_active=True)
    outsider = django_user_model.objects.create_user(email="outsider@field.test", company=other, role="EMPLOYEE", is_active=True)
    platform = django_user_model.objects.create_superuser(email="platform@field.test", full_name="Platform", password="test-password")
    activity = FieldActivity.objects.create(company=company, employee=worker, activity_type="DELIVERY", title="Route")
    stop = FieldStop.objects.create(activity=activity, stop_type="DELIVERY", sequence=1)
    return worker, outsider, platform, activity, stop


@pytest.mark.parametrize("actor_index", [1, 2])
def test_other_company_and_platform_cannot_create_stops(field_context, actor_index):
    actor = field_context[actor_index]
    activity = field_context[3]
    serializer = FieldStopSerializer(data={"activity": str(activity.pk), "stop_type": "DELIVERY", "sequence": 2},
        context={"request": SimpleNamespace(user=actor)})
    assert not serializer.is_valid()
    assert FieldStop.objects.filter(activity=activity).count() == 1


@pytest.mark.parametrize("actor_index", [1, 2])
def test_other_company_and_platform_cannot_read_or_patch_stops(field_context, actor_index):
    client = APIClient()
    client.force_authenticate(field_context[actor_index])
    stop = field_context[4]
    url = f"/api/v1/field-stops/{stop.pk}/"
    assert client.get(url).status_code == 404
    assert client.patch(url, {"notes": "Unauthorized change"}).status_code == 404
    stop.refresh_from_db()
    assert stop.notes == ""


def test_assigned_worker_retains_stop_access(field_context):
    worker, _, _, activity, stop = field_context
    client = APIClient()
    client.force_authenticate(worker)
    assert client.get(f"/api/v1/field-stops/{stop.pk}/").status_code == 200
    response = client.post("/api/v1/field-stops/", {"activity": str(activity.pk), "stop_type": "DELIVERY", "sequence": 2})
    assert response.status_code == 201, response.data


def test_partial_serializer_update_checks_existing_activity(field_context):
    serializer = FieldStopSerializer(field_context[4], data={"notes": "Unauthorized"}, partial=True,
        context={"request": SimpleNamespace(user=field_context[1])})
    assert not serializer.is_valid()


def test_platform_identity_with_company_cannot_create_field_activity(field_context):
    worker, _, platform, activity, _ = field_context
    platform.company = activity.company
    serializer = FieldActivitySerializer(data={"employee": str(worker.pk), "activity_type": "DELIVERY", "title": "Denied"},
        context={"request": SimpleNamespace(user=platform)})
    assert not serializer.is_valid()
