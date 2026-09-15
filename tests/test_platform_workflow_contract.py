from types import SimpleNamespace
from django.test import TestCase
from companies.models import Company
from subscriptions.models import Plan, Subscription
from users.models import User
from platform_admin.serializers import PlatformCompanySerializer
from platform_admin.views import PlatformSubscriptionViewSet

class PlatformWorkflowContractTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Workflow company")
        self.plan = Plan.objects.create(name="Workflow plan", max_users=10, max_projects=5, price_monthly="10.00")
        Subscription.objects.create(company=self.company, plan=self.plan)
        self.admin = User.objects.create_superuser(email="workflow-admin@example.test", full_name="Admin", password="Test-password-123")

    def test_company_response_has_real_subscription_and_counts(self):
        data = PlatformCompanySerializer(self.company, context={"request": SimpleNamespace(user=self.admin)}).data
        self.assertEqual(data["subscription_plan"], "Workflow plan")
        self.assertTrue(data["subscription_active"])
        self.assertEqual(data["branches_count"], 0)
        self.assertEqual(data["projects_count"], 0)
        self.assertEqual(data["allowed_actions"], ["DEACTIVATE"])
        self.company.is_active = False
        self.assertEqual(PlatformCompanySerializer(self.company, context={"request": SimpleNamespace(user=self.admin)}).data["allowed_actions"], ["REACTIVATE"])

    def test_actions_not_advertised_without_authorized_request(self):
        self.assertEqual(PlatformCompanySerializer(self.company).data["allowed_actions"], [])

    def test_subscription_search_filters_before_pagination(self):
        view = PlatformSubscriptionViewSet()
        view.request = SimpleNamespace(query_params={"search": "Workflow company"})
        self.assertEqual(view.get_queryset().count(), 1)
        view.request = SimpleNamespace(query_params={"search": "no match"})
        self.assertEqual(view.get_queryset().count(), 0)
