from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.roles import Roles
from users.models import User

from .models import Plan, Subscription


class SubscriptionUsageAPITests(APITestCase):
	def setUp(self):
		self.company = Company.objects.create(name="Acme Manufacturing")
		self.admin = User.objects.create_user(
			email="admin@acme.test",
			password="password123",
			full_name="Company Admin",
			role=Roles.ADMIN,
			company=self.company,
			is_active=True,
		)
		plan = Plan.objects.create(
			name="Test Plan",
			max_users=10,
			max_projects=5,
			max_branches=2,
			storage_limit_bytes=2048,
			ai_analytics_enabled=True,
			reports_enabled=True,
			price_monthly=10,
		)
		Subscription.objects.create(company=self.company, plan=plan)
		self.client.force_authenticate(self.admin)

	def test_usage_and_features_are_available_to_company_admin(self):
		usage_response = self.client.get("/api/subscriptions/usage/")
		features_response = self.client.get("/api/subscriptions/features/")

		self.assertEqual(usage_response.status_code, status.HTTP_200_OK)
		self.assertEqual(usage_response.data["users"]["used"], 1)
		self.assertEqual(usage_response.data["branches"]["limit"], 2)
		self.assertEqual(features_response.status_code, status.HTTP_200_OK)
		self.assertTrue(features_response.data["features"]["ADVANCED_ANALYTICS"])
