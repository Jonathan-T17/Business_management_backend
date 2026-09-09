from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from companies.models import Company
from core.roles import Roles
from core.visibility import VisibilityService
from reports.models import Report
from users.models import User
from workflows.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStepInstance,
    WorkflowStepRecipient,
)


class ReportVisibilityTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Visibility Test Company")
        self.user = User.objects.create_user(
            email="report-user@test.com",
            password="password123",
            full_name="Report User",
            role=Roles.EMPLOYEE,
            company=self.company,
            is_active=True,
        )
        self.report = Report.objects.create(
            title="Workflow Report",
            description="Visible via workflow assignment",
            report_type="GENERAL",
            company=self.company,
            created_by=self.user,
            visibility="COMPANY",
        )

        self.workflow_definition = WorkflowDefinition.objects.create(
            company=self.company,
            name="Report Review",
            code="report-review",
            target_type="REPORT",
            created_by=self.user,
        )
        self.workflow_instance = WorkflowInstance.objects.create(
            company=self.company,
            workflow=self.workflow_definition,
            content_type=ContentType.objects.get_for_model(Report),
            object_id=str(self.report.id),
            submitted_by=self.user,
        )
        self.step = WorkflowStepInstance.objects.create(
            workflow_instance=self.workflow_instance,
            name="Review",
            order=1,
            approval_mode="ANY",
            can_reject=True,
            can_return=True,
            status="WAITING",
        )
        WorkflowStepRecipient.objects.create(
            step=self.step,
            user=self.user,
            status="PENDING",
        )

    def test_workflow_recipients_are_included_without_uuid_string_mismatch(self):
        queryset = VisibilityService.reports_queryset(
            user=self.user,
            queryset=Report.objects.all(),
        )

        self.assertIn(self.report, queryset)

