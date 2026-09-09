from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from companies.models import Company
from core.roles import Roles
from users.models import User


class UserAdminSafetyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.admin = User.objects.create_user(
            email="admin@acme.test",
            full_name="Acme Admin",
            password="secure-pass-123",
            company=self.company,
            role=Roles.ADMIN,
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_last_admin_cannot_self_deactivate(self):
        response = self.client.post(f"/api/users/{self.admin.id}/deactivate/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_last_admin_cannot_demote_self(self):
        response = self.client.post(
            f"/api/users/{self.admin.id}/role/",
            {"role": Roles.MANAGER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Roles.ADMIN)

