from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.roles import Roles
from users.models import User

from .models import FormField, FormTemplate


class FormTemplateBuilderAPITests(APITestCase):
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
		self.template = FormTemplate.objects.create(
			company=self.company,
			name="Daily Production",
			code="daily-production",
			category="PRODUCTION",
			created_by=self.admin,
		)
		self.first_field = FormField.objects.create(
			template=self.template,
			key="quantity",
			label="Quantity",
			field_type="DECIMAL",
			order=0,
		)
		self.second_field = FormField.objects.create(
			template=self.template,
			key="notes",
			label="Notes",
			field_type="LONG_TEXT",
			order=1,
		)
		self.client.force_authenticate(self.admin)

	def test_admin_can_publish_template(self):
		response = self.client.post(
			f"/api/form-templates/{self.template.id}/publish/",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["lifecycle_status"], "PUBLISHED")

	def test_admin_can_reorder_template_fields(self):
		response = self.client.post(
			f"/api/form-templates/{self.template.id}/reorder-fields/",
			{"field_ids": [self.second_field.id, self.first_field.id]},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.first_field.refresh_from_db()
		self.second_field.refresh_from_db()
		self.assertEqual(self.second_field.order, 0)
		self.assertEqual(self.first_field.order, 1)
