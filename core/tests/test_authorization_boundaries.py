from types import SimpleNamespace

from django.test import TestCase

from companies.models import Company
from core.authorization import Authorization
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.tenant import TenantService
from core.visibility import VisibilityService
from core.roles import Roles
from users.models import User


class AuthorizationBoundaryTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Tenant A")
        self.company_b = Company.objects.create(name="Tenant B")

        self.admin_a = User.objects.create_user(
            email="admin-a@example.test",
            full_name="Admin A",
            password="test-pass-12345",
            company=self.company_a,
            role=Roles.ADMIN,
            is_active=True,
        )
        self.employee_a = User.objects.create_user(
            email="employee-a@example.test",
            full_name="Employee A",
            password="test-pass-12345",
            company=self.company_a,
            role=Roles.EMPLOYEE,
            is_active=True,
        )
        self.employee_b = User.objects.create_user(
            email="employee-b@example.test",
            full_name="Employee B",
            password="test-pass-12345",
            company=self.company_b,
            role=Roles.EMPLOYEE,
            is_active=True,
        )
        self.platform = User.objects.create_superuser(
            email="platform@example.test",
            full_name="Platform Admin",
            password="test-pass-12345",
        )

    def test_platform_identity_has_platform_capabilities_only(self):
        self.assertTrue(CapabilityService.has(self.platform, Capabilities.PLATFORM_ADMIN))
        self.assertTrue(CapabilityService.has(self.platform, Capabilities.VIEW_PLATFORM_SECURITY))
        self.assertFalse(CapabilityService.has(self.platform, Capabilities.MANAGE_EMPLOYEES))
        self.assertFalse(CapabilityService.has(self.platform, Capabilities.VIEW_COMPENSATION))

    def test_company_admin_gets_safe_configuration_defaults(self):
        self.assertTrue(CapabilityService.has(self.admin_a, Capabilities.MANAGE_EMPLOYEES))
        self.assertTrue(CapabilityService.has(self.admin_a, Capabilities.MANAGE_WORKFLOWS))
        self.assertTrue(CapabilityService.has(self.admin_a, Capabilities.MANAGE_SUBSCRIPTION))
        self.assertFalse(CapabilityService.has(self.admin_a, Capabilities.VIEW_COMPENSATION))
        self.assertFalse(CapabilityService.has(self.admin_a, Capabilities.VIEW_FIELD_LOCATION))
        self.assertFalse(CapabilityService.has(self.admin_a, Capabilities.PLATFORM_ADMIN))

    def test_platform_identity_is_not_a_tenant_identity(self):
        self.assertTrue(Authorization.is_platform_superuser(self.platform))
        self.assertFalse(Authorization.is_tenant_user(self.platform))
        self.assertFalse(
            VisibilityService.same_company(
                self.platform,
                SimpleNamespace(company_id=self.company_a.id),
            )
        )

    def test_tenant_user_cannot_cross_company_boundary(self):
        self.assertTrue(
            VisibilityService.same_company(
                self.admin_a,
                SimpleNamespace(company_id=self.company_a.id),
            )
        )
        self.assertFalse(
            VisibilityService.same_company(
                self.admin_a,
                SimpleNamespace(company_id=self.company_b.id),
            )
        )

    def test_tenant_service_never_exposes_global_users_to_platform_identity(self):
        self.assertFalse(TenantService.users(self.platform).exists())

    def test_company_admin_user_list_is_tenant_scoped(self):
        ids = set(TenantService.users(self.admin_a).values_list("id", flat=True))
        self.assertIn(self.admin_a.id, ids)
        self.assertIn(self.employee_a.id, ids)
        self.assertNotIn(self.employee_b.id, ids)
