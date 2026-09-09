from django.test import TestCase

from companies.models import Company
from core.authorization import Authorization
from users.models import User


class AuthenticationPolicyTests(TestCase):

	def test_inactive_company_cannot_authenticate_user(self):
		company = Company.objects.create(
			name="Inactive Company",
			is_active=False,
		)
		user = User.objects.create_user(
			email="employee@example.com",
			full_name="Employee",
			password="Strong-test-password-123!",
			role="EMPLOYEE",
			company=company,
			is_active=True,
		)

		self.assertFalse(Authorization.can_authenticate(user))
