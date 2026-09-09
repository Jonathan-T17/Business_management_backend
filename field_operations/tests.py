from django.core.exceptions import ValidationError
from django.test import TestCase

from companies.models import Company
from company_setup.models import FieldActivityTemplate
from core.roles import Roles
from users.models import User

from .models import FieldActivity
from .services import FieldOperationService


class FieldTemplateEnforcementTests(TestCase):
	def test_location_required_template_blocks_start_without_coordinates(self):
		company = Company.objects.create(name="Acme Manufacturing")
		employee = User.objects.create_user(
			email="employee@acme.test",
			password="password123",
			full_name="Employee",
			role=Roles.EMPLOYEE,
			company=company,
			is_active=True,
		)
		FieldActivityTemplate.objects.create(
			company=company,
			name="Delivery Template",
			activity_type="DELIVERY",
			require_location=True,
		)
		activity = FieldActivity.objects.create(
			company=company,
			employee=employee,
			activity_type="DELIVERY",
			title="Deliver supplies",
			created_by=employee,
		)

		with self.assertRaisesMessage(
			ValidationError,
			"requires a location check-in",
		):
			FieldOperationService.start_activity(
				activity=activity,
				user=employee,
			)
