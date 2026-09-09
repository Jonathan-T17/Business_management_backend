from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from users.models import User
from core.roles import Roles

from .models import SupportMessage, SupportTicket


class SupportTicketAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Support Test Company")
        self.user = User.objects.create_user(
            email="employee@support.test",
            password="password123",
            full_name="Employee",
            role=Roles.EMPLOYEE,
            company=self.company,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin@support.test",
            password="password123",
            full_name="Admin",
            role=Roles.ADMIN,
            company=self.company,
            is_active=True,
        )
        self.platform_user = User.objects.create_user(
            email="platform@support.test",
            password="password123",
            full_name="Platform Support",
            role=Roles.SUPERUSER,
            is_superuser=True,
            is_active=True,
        )

    def test_user_profile_exposes_effective_authority(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["capabilities"], [])
        self.assertIn("CONTACT_SMARTBIZ_SUPPORT", response.data["allowed_actions"])

    def test_employee_ticket_context_is_allowlisted_and_tenant_scoped(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/support/tickets/",
            {
                "category": "TECHNICAL",
                "subject": "Something is broken",
                "description": "The page fails to load.",
                "context": {
                    "page": "/reports",
                    "module": "reporting",
                    "password": "must-not-be-stored",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = SupportTicket.objects.get()
        self.assertEqual(ticket.company_id, self.company.id)
        self.assertNotIn("password", ticket.context)
        self.assertEqual(self.client.get("/api/support/tickets/").data[0]["id"], str(ticket.id))

    def test_platform_can_reply_and_company_user_can_read_reply(self):
        ticket = SupportTicket.objects.create(
            company=self.company,
            created_by=self.user,
            category="TECHNICAL",
            subject="System error",
            description="Details",
        )
        self.client.force_authenticate(self.platform_user)
        response = self.client.post(
            f"/api/support/tickets/{ticket.id}/reply/",
            {"body": "We are investigating this."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupportMessage.objects.count(), 1)

        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/support/tickets/{ticket.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["messages"]), 1)

    def test_inactive_company_cannot_use_support(self):
        self.company.is_active = False
        self.company.save(update_fields=("is_active",))
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/support/tickets/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_messages_and_platform_support_routes_are_available(self):
        ticket = SupportTicket.objects.create(
            company=self.company,
            created_by=self.user,
            category="TECHNICAL",
            subject="System error",
            description="Details",
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/support/tickets/{ticket.id}/messages/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/api/platform/support/tickets/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.platform_user)
        response = self.client.get("/api/platform/support/tickets/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
