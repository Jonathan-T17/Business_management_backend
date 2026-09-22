"""Tenant-only queryset helpers.

IMPORTANT: platform identities intentionally receive no tenant business data
from this service. Platform Control Center endpoints must use dedicated
platform selectors/services instead. Complex business visibility delegates to
VisibilityService so there is one object-visibility policy.
"""

from activity.models import ActivityLog
from analytics_ai.models import AIInsight, AnalyticsSnapshot
from companies.models import Branch, Company, CompanyInvite
from notifications.models import Notification
from projects.models import Project, ProjectMembership
from reports.models import Report, ReportComment
from subscriptions.models import Subscription
from tasks.models import Task
from users.models import User

from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class TenantService:
    @staticmethod
    def _tenant(user):
        return CapabilityService.is_tenant_identity(user)

    @staticmethod
    def users(user):
        if not TenantService._tenant(user):
            return User.objects.none()

        queryset = User.objects.filter(company_id=user.company_id, is_deleted=False)
        if CapabilityService.has(user, Capabilities.VIEW_ALL_EMPLOYEES) or CapabilityService.has(
            user, Capabilities.MANAGE_EMPLOYEES
        ):
            return queryset
        return queryset.filter(pk=user.pk)

    @staticmethod
    def companies(user):
        if not TenantService._tenant(user):
            return Company.objects.none()
        return Company.objects.filter(pk=user.company_id)

    @staticmethod
    def branches(user):
        if not TenantService._tenant(user):
            return Branch.objects.none()

        queryset = Branch.objects.filter(company_id=user.company_id, is_active=True)
        if CapabilityService.has(user, Capabilities.MANAGE_ORGANIZATION):
            return queryset
        if not getattr(user, "branch_id", None):
            return queryset.none()
        return queryset.filter(pk=user.branch_id)

    @staticmethod
    def projects(user):
        from core.visibility import VisibilityService

        return VisibilityService.projects_queryset(
            user=user,
            queryset=Project.objects.filter(is_active=True),
        )

    @staticmethod
    def project_memberships(user):
        if not TenantService._tenant(user):
            return ProjectMembership.objects.none()

        visible_projects = TenantService.projects(user).values_list("pk", flat=True)
        return ProjectMembership.objects.filter(project_id__in=visible_projects)

    @staticmethod
    def tasks(user):
        from core.visibility import VisibilityService

        return VisibilityService.tasks_queryset(
            user=user,
            queryset=Task.objects.filter(is_active=True),
        )

    @staticmethod
    def reports(user):
        from core.visibility import VisibilityService

        return VisibilityService.reports_queryset(
            user=user,
            queryset=Report.objects.all(),
        )

    @staticmethod
    def comments(user):
        if not TenantService._tenant(user):
            return ReportComment.objects.none()
        visible_report_ids = TenantService.reports(user).values_list("pk", flat=True)
        return ReportComment.objects.filter(report_id__in=visible_report_ids)

    @staticmethod
    def notifications(user):
        if not TenantService._tenant(user):
            return Notification.objects.filter(recipient=user)
        return Notification.objects.filter(recipient=user, company_id=user.company_id)

    @staticmethod
    def activity(user):
        if not TenantService._tenant(user):
            return ActivityLog.objects.none()
        # Activity is not authoritative audit and must not broaden visibility.
        return ActivityLog.objects.filter(company_id=user.company_id, user=user)

    @staticmethod
    def invites(user):
        if not TenantService._tenant(user) or not CapabilityService.has(
            user, Capabilities.MANAGE_EMPLOYEES
        ):
            return CompanyInvite.objects.none()
        return CompanyInvite.objects.filter(company_id=user.company_id)

    @staticmethod
    def subscriptions(user):
        if not TenantService._tenant(user):
            return Subscription.objects.none()
        return Subscription.objects.filter(company_id=user.company_id)

    @staticmethod
    def analytics_snapshots(user):
        if not TenantService._tenant(user) or not CapabilityService.has_company(
            user, Capabilities.VIEW_COMPANY_ANALYTICS
        ):
            return AnalyticsSnapshot.objects.none()
        return AnalyticsSnapshot.objects.filter(company_id=user.company_id)

    @staticmethod
    def ai_insights(user):
        if not TenantService._tenant(user) or not CapabilityService.has_company(
            user, Capabilities.VIEW_COMPANY_ANALYTICS
        ):
            return AIInsight.objects.none()
        return AIInsight.objects.filter(company_id=user.company_id)

    @staticmethod
    def filter(queryset, user):
        """Safe fallback for simple tenant-owned models only.

        Complex models should have an explicit VisibilityService selector.
        Platform identities deliberately get no rows here.
        """
        if not TenantService._tenant(user):
            return queryset.none()

        model = queryset.model
        field_names = {field.name for field in model._meta.get_fields()}

        if "company" not in field_names:
            return queryset.none()

        return queryset.filter(company_id=user.company_id)
