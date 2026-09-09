from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.roles import Roles
from users.models import User

from .models import ActiveSession, AuditLog


class CompanySecurityCenterAPITests(APITestCase):
	def setUp(self):
		self.company = Company.objects.create(name="Acme Manufacturing")
		self.other_company = Company.objects.create(name="Other Company")
		self.admin = User.objects.create_user(
			email="admin@acme.test",
			password="password123",
			full_name="Company Admin",
			role=Roles.ADMIN,
			company=self.company,
			is_active=True,
		)
		self.employee = User.objects.create_user(
			email="employee@acme.test",
			password="password123",
			full_name="Employee",
			role=Roles.EMPLOYEE,
			company=self.company,
			is_active=True,
		)
		self.session = ActiveSession.objects.create(
			user=self.employee,
			company=self.company,
			refresh_token_jti="acme-session",
			ip_address="127.0.0.1",
			browser="Browser",
			operating_system="OS",
			device="Desktop",
		)
		AuditLog.objects.create(
			user=self.employee,
			company=self.company,
			action="SECURITY",
			description="Acme security event",
		)
		AuditLog.objects.create(
			company=self.other_company,
			action="SECURITY",
			description="Other security event",
		)
		self.client.force_authenticate(self.admin)

	def test_audit_logs_are_scoped_to_company(self):
		response = self.client.get("/api/company-audit-logs/")

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)
		self.assertEqual(response.data[0]["description"], "Acme security event")

	def test_admin_can_terminate_company_session(self):
		response = self.client.post(
			f"/api/company-active-sessions/{self.session.id}/terminate/",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.session.refresh_from_db()
		self.assertFalse(self.session.is_active)
		self.assertIsNotNone(self.session.terminated_at)
