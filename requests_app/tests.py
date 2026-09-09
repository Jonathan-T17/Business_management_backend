import uuid
from unittest.mock import patch

from django.test import TestCase

from companies.models import Company
from core.visibility import VisibilityService
from users.models import User

from .models import BusinessRequest


class BusinessRequestVisibilityTests(TestCase):

	def test_workflow_ids_are_compared_as_text(self):
		company = Company.objects.create(name="Test Company")
		user = User(
			id=uuid.uuid4(),
			role="EMPLOYEE",
			company=company,
		)

		with patch.object(
			VisibilityService,
			"workflow_object_ids",
			return_value=[str(uuid.uuid4())],
		):
			queryset = VisibilityService.business_requests_queryset(
				user=user,
				queryset=BusinessRequest.objects.all(),
			)

		self.assertIn("::varchar", str(queryset.query))
