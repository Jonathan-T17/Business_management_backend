from django.test import TestCase
from django.core.exceptions import ValidationError

from companies.models import Company, CompanyInvite
from core.roles import Roles
from organizations.models import EmployeeProfile
from users.models import User
from users.services import TenantUserLifecycleService


class TenantIdentitySafetyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Phase2 Co")
        self.admin = User.objects.create_user(
            email="admin@phase2.test", full_name="Admin", password="safe-pass-123",
            company=self.company, role=Roles.ADMIN, is_active=True, email_verified=True, account_state="ACTIVE",
        )
        self.company.created_by = self.admin
        self.company.save(update_fields=["created_by"])

    def test_tenant_admin_is_not_django_staff(self):
        self.admin.save()
        self.assertFalse(self.admin.is_staff)

    def test_last_admin_cannot_be_deactivated(self):
        with self.assertRaises(ValidationError):
            TenantUserLifecycleService.deactivate(
                actor=self.admin, target=self.admin, reason="test"
            )

    def test_company_can_have_second_admin(self):
        second = User.objects.create_user(
            email="second@phase2.test", full_name="Second", password="safe-pass-123",
            company=self.company, role=Roles.EMPLOYEE, is_active=True, email_verified=True, account_state="ACTIVE",
        )
        TenantUserLifecycleService.change_role(
            actor=self.admin, target=second, new_role=Roles.ADMIN, reason="backup admin"
        )
        second.refresh_from_db()
        self.assertEqual(second.role, Roles.ADMIN)
        self.assertFalse(second.is_staff)

    def test_email_verification_does_not_reactivate_deactivated_account(self):
        user = User.objects.create_user(
            email="disabled@phase2.test", full_name="Disabled", password="safe-pass-123",
            company=self.company, role=Roles.EMPLOYEE, is_active=False, email_verified=False, account_state="DEACTIVATED",
        )
        TenantUserLifecycleService.verify_email(user=user)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(user.account_state, "DEACTIVATED")

    def test_employee_ids_are_tenant_scoped(self):
        u1 = User.objects.create_user(email="e1@phase2.test", full_name="E1", password="x", company=self.company)
        EmployeeProfile.objects.create(user=u1, company=self.company, employee_id="EMP-001")
        other = Company.objects.create(name="Other Co")
        u2 = User.objects.create_user(email="e2@other.test", full_name="E2", password="x", company=other)
        EmployeeProfile.objects.create(user=u2, company=other, employee_id="EMP-001")
