from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from security.models import ActiveSession
from users.models import User
from core.roles import Roles


class PlatformFrontendContractTests(APITestCase):
	def setUp(self):
		self.company = Company.objects.create(name="Platform Contract Company")
		self.platform_user = User.objects.create_user(
			email="platform-contract@test.com",
			password="password123",
			full_name="Platform Operator",
			role=Roles.SUPERUSER,
			is_superuser=True,
			is_active=True,
		)
		self.target = User.objects.create_user(
			email="target-contract@test.com",
			password="password123",
			full_name="Target User",
			role=Roles.EMPLOYEE,
			company=self.company,
			is_active=True,
		)
		self.client.force_authenticate(self.platform_user)

	def test_canonical_and_short_session_endpoints_are_available(self):
		for url in ("/api/platform/security/sessions/", "/api/platform/sessions/"):
			response = self.client.get(url)
			self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_platform_user_actions_require_reason_and_change_state(self):
		url = f"/api/platform/users/{self.target.id}/deactivate/"
		response = self.client.post(url, {}, format="json")
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

		response = self.client.post(url, {"reason": "Security review"}, format="json")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.target.refresh_from_db()
		self.assertFalse(self.target.is_active)

		response = self.client.post(
			f"/api/platform/users/{self.target.id}/require-password-reset/",
			{"reason": "Security review"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.target.refresh_from_db()
		self.assertTrue(self.target.must_change_password)

		response = self.client.post(
			f"/api/platform/users/{self.target.id}/reactivate/",
			{"reason": "Review completed"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_platform_settings_are_safe_read_only_configuration(self):
		response = self.client.get("/api/platform/settings/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertFalse(response.data["editable"])
		self.assertNotIn("SECRET_KEY", response.data)

	def test_platform_plan_catalog_is_available(self):
		response = self.client.get("/api/platform/plans/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_platform_user_list_serializes_allowed_actions(self):
		response = self.client.get("/api/platform/users/")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertGreater(len(response.data), 0)
		self.assertIn("allowed_actions", response.data[0])

# Create your tests here.
