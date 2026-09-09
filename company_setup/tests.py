from rest_framework import status
from rest_framework.test import APITestCase

from companies.models import Company
from core.roles import Roles
from organizations.models import Department
from users.models import User
from forms_engine.models import FormField

from .models import BusinessSetupTemplate, ReportingProcess


class CompanySetupAPITests(APITestCase):
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
        self.template = BusinessSetupTemplate.objects.create(
            code="test-template",
            name="Test Template",
            configuration={"departments": ["Operations"]},
        )
        self.client.force_authenticate(self.admin)

    def test_status_returns_frontend_setup_steps(self):
        response = self.client.get("/api/company-setup/status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["progress"], 0)
        self.assertEqual(response.data["steps"][0]["code"], "company")

    def test_admin_can_update_resumable_onboarding_state(self):
        response = self.client.patch(
            "/api/company-setup/onboarding/",
            {
                "current_step": "reporting",
                "completed_steps": ["company", "organization"],
                "skipped_steps": ["employees"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_step"], "reporting")
        self.assertEqual(response.data["completed_steps"], ["company", "organization"])
        self.assertEqual(response.data["skipped_steps"], ["employees"])

    def test_apply_template_is_idempotent(self):
        url = f"/api/company-setup/templates/{self.template.code}/apply/"

        first_response = self.client.post(url, {"departments": True}, format="json")
        second_response = self.client.post(url, {"departments": True}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data["created"]["departments"], 1)
        self.assertEqual(second_response.data["created"]["departments"], 0)
        self.assertEqual(
            Department.objects.filter(company=self.company, name="Operations").count(),
            1,
        )

    def test_admin_can_create_safe_tenant_role_preset(self):
        response = self.client.post(
            "/api/company-setup/role-presets/",
            {
                "code": "site-supervisor",
                "name": "Site Supervisor",
                "capabilities": ["MANAGE_TASKS"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company"], self.company.id)

    def test_platform_capability_is_rejected_from_tenant_preset(self):
        response = self.client.post(
            "/api/company-setup/role-presets/",
            {
                "code": "unsafe",
                "name": "Unsafe",
                "capabilities": ["PLATFORM_ADMIN"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_create_request_type_definition(self):
        response = self.client.post(
            "/api/company-setup/request-types/",
            {
                "code": "fuel-request",
                "name": "Fuel Request",
                "amount_enabled": True,
                "amount_required": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["company"], self.company.id)

    def test_request_type_cannot_require_disabled_field(self):
        response = self.client.post(
            "/api/company-setup/request-types/",
            {
                "code": "invalid-request",
                "name": "Invalid Request",
                "amount_enabled": False,
                "amount_required": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_activate_field_template(self):
        create_response = self.client.post(
            "/api/company-setup/field-templates/",
            {
                "name": "Delivery",
                "activity_type": "DELIVERY",
                "require_location": True,
                "is_active": False,
            },
            format="json",
        )

        response = self.client.post(
            f"/api/company-setup/field-templates/{create_response.data['id']}/activate/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_active"])

    def test_admin_can_create_approval_route(self):
        response = self.client.post(
            "/api/company-setup/approval-routes/",
            {
                "name": "Purchase Approval",
                "steps": [
                    {"recipient_type": "COMPANY_ADMIN", "name": "Final Approval"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["steps"][0]["name"], "Final Approval")

    def test_admin_can_create_reporting_process_transactionally(self):
        response = self.client.post(
            "/api/company-setup/reporting-processes/",
            {
                "name": "Daily Production Report",
                "submitters": {"type": "ROLE", "role": "EMPLOYEE"},
                "schedule": {"frequency": "DAILY", "due_time": "17:30:00"},
                "fields": [
                    {
                        "key": "production_quantity",
                        "label": "Production Quantity",
                        "type": "DECIMAL",
                        "required": True,
                    },
                ],
                "approval_steps": [
                    {"recipient_type": "COMPANY_ADMIN", "name": "Operations Approval"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["schedule"])
        self.assertIsNotNone(response.data["template"])
        self.assertIsNotNone(response.data["approval_route"])

    def test_admin_can_replace_approval_route_steps(self):
        create_response = self.client.post(
            "/api/company-setup/approval-routes/",
            {
                "name": "Purchase Approval",
                "steps": [{"recipient_type": "COMPANY_ADMIN"}],
            },
            format="json",
        )

        response = self.client.patch(
            f"/api/company-setup/approval-routes/{create_response.data['id']}/",
            {
                "steps": [
                    {"recipient_type": "ROLE", "recipient_role": "MANAGER", "name": "Manager"},
                    {"recipient_type": "COMPANY_ADMIN", "name": "Final Approval"},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["steps"]), 2)
        self.assertEqual(response.data["steps"][1]["name"], "Final Approval")

    def test_admin_can_replace_reporting_fields_and_schedule(self):
        create_response = self.client.post(
            "/api/company-setup/reporting-processes/",
            {
                "name": "Daily Production Report",
                "submitters": {"type": "ROLE", "role": "EMPLOYEE"},
                "schedule": {"frequency": "DAILY", "due_time": "17:30:00"},
                "fields": [{"key": "quantity", "label": "Quantity", "type": "DECIMAL"}],
            },
            format="json",
        )

        response = self.client.patch(
            f"/api/company-setup/reporting-processes/{create_response.data['id']}/",
            {
                "fields": [{"key": "notes", "label": "Notes", "type": "LONG_TEXT", "required": True}],
                "schedule": {"due_time": "18:00:00"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        process = response.data
        self.assertIsNotNone(process["template"])
        stored_process = ReportingProcess.objects.get(pk=process["id"])
        self.assertEqual(stored_process.schedule.due_time.isoformat(), "18:00:00")
        self.assertEqual(
            FormField.objects.get(template_id=process["template"]).key,
            "notes",
        )