import pytest
from rest_framework.test import APIClient

from django.test import RequestFactory
from security.services import create_active_session
from rest_framework_simplejwt.tokens import RefreshToken

def bound_access_token(user):
    refresh = RefreshToken.for_user(user)
    session = create_active_session(RequestFactory().get("/"), user, refresh["jti"])
    refresh["sid"] = str(session.pk)
    return refresh.access_token



from companies.models import Company
from support.models import SupportMessage, SupportTicket


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["ADMIN", "EMPLOYEE"])
def test_created_request_can_be_opened_and_replied_to(django_user_model, role):
    company = Company.objects.create(name="Support journey")
    actor = django_user_model.objects.create_user(
        email="support-journey@example.test", company=company, role=role,
        is_active=True, account_state="ACTIVE", email_verified=True,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {bound_access_token(actor)}")
    response = client.post("/api/v1/support/tickets/", {
        "category": "TECHNICAL",
        "subject": "Cannot find invitations",
        "description": "Please help me find where to invite colleagues.",
        "requested_priority": "HIGH",
        "context": {"page": "/employees", "object_id": "REF-1", "password": "omit-me"},
    }, format="json")
    assert response.status_code == 201, response.data
    ticket = SupportTicket.objects.get()
    assert response.data["id"] == str(ticket.pk)
    assert response.data["reference"] == ticket.reference
    assert response.data["status"] == "OPEN"
    assert response.data["priority"] == "HIGH"
    assert response.data["requested_priority"] == "HIGH"
    assert response.data["messages"] == []
    assert ticket.context["page"] == "/employees"
    assert ticket.context["object_id"] == "REF-1"
    assert "password" not in ticket.context

    url = f"/api/v1/support/tickets/{response.data['id']}/"
    assert client.get(url).data["subject"] == "Cannot find invitations"
    reply = client.post(url + "reply/", {"body": "More information."}, format="json")
    assert reply.status_code == 201, reply.data
    SupportMessage.objects.create(ticket=ticket, author=actor, body="Internal", visibility="INTERNAL")
    assert [item["body"] for item in client.get(url).data["messages"]] == ["More information."]

    other = Company.objects.create(name="Other company")
    outsider = django_user_model.objects.create_user(
        email="other-support@example.test", company=other, role="ADMIN",
        is_active=True, account_state="ACTIVE", email_verified=True,
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {bound_access_token(outsider)}")
    assert client.get(url).status_code == 404
    assert client.post(url + "reply/", {"body": "No access"}, format="json").status_code == 404


@pytest.mark.django_db
def test_support_rejects_non_object_context(django_user_model):
    company = Company.objects.create(name="Support validation")
    actor = django_user_model.objects.create_user(email="support-validation@example.test", company=company)
    client = APIClient()
    client.force_authenticate(actor)
    response = client.post("/api/v1/support/tickets/", {
        "category": "TECHNICAL", "subject": "Test", "description": "Test", "context": ["invalid"],
    }, format="json")
    assert response.status_code == 400
    assert not SupportTicket.objects.exists()
