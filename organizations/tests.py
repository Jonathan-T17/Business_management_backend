from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.capabilities import Capabilities
from core.roles import Roles
from organizations.models import (
    EmployeeDelegation,
    EmployeeProfile,
    EmployeeReplacement,
    Position,
    PositionCapabilityGrant,
)
from organizations.services import (
    DelegationService,
    EmployeeLifecycleService,
    EmployeeReplacementService,
)
from users.models import User


class EmployeeLifecycleModelAndServiceTests(TestCase):
    def test_lifecycle_models_and_services_are_defined(self):
        self.assertTrue(hasattr(EmployeeProfile, "termination_date"))
        self.assertTrue(hasattr(EmployeeProfile, "termination_reason"))
        self.assertTrue(hasattr(EmployeeProfile, "terminated_by"))

        self.assertTrue(hasattr(EmployeeDelegation, "status"))
        self.assertTrue(hasattr(EmployeeReplacement, "status"))

        self.assertTrue(hasattr(User, "must_change_password"))
        self.assertTrue(hasattr(User, "password_reset_required_at"))

        self.assertTrue(hasattr(EmployeeLifecycleService, "place_on_leave"))
        self.assertTrue(hasattr(DelegationService, "create"))
        self.assertTrue(hasattr(EmployeeReplacementService, "execute"))


class CapabilityConfigurationAPITests(APITestCase):
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
        self.position = Position.objects.create(
            company=self.company,
            title="Operations Manager",
        )
        self.client.force_authenticate(self.admin)

    def test_catalogue_marks_platform_capabilities_unassignable(self):
        response = self.client.get(reverse("capability-catalogue"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        platform_capability = next(
            capability
            for capability in response.data["capabilities"]
            if capability["code"] == Capabilities.PLATFORM_ADMIN
        )
        self.assertFalse(
            platform_capability["assignable_by_company_admin"]
        )

    def test_company_admin_cannot_grant_platform_capability(self):
        response = self.client.post(
            reverse("position-capability-grant-grant"),
            {
                "position": self.position.id,
                "capability": Capabilities.PLATFORM_ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            PositionCapabilityGrant.objects.filter(
                position=self.position,
                capability=Capabilities.PLATFORM_ADMIN,
            ).exists()
        )

    def test_company_admin_can_apply_role_preset_to_position(self):
        response = self.client.post(
            reverse("role-preset-apply"),
            {
                "position": self.position.id,
                "preset": "OPERATIONS_MANAGER",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preset"], "OPERATIONS_MANAGER")
        self.assertTrue(
            PositionCapabilityGrant.objects.filter(
                position=self.position,
                capability=Capabilities.MANAGE_PROJECTS,
                is_active=True,
            ).exists()
        )
