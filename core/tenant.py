from users.models import User
from companies.models import Company, Branch, CompanyInvite
from projects.models import Project, ProjectMembership
from tasks.models import Task
from reports.models import Report, ReportComment
from notifications.models import Notification
from activity.models import ActivityLog
from subscriptions.models import Subscription
from analytics_ai.models import AnalyticsSnapshot, AIInsight

from core.roles import Roles


class TenantService:
    """
    Centralized multi-tenant visibility rules.

    SUPERUSER:
        Global platform access.

    ADMIN:
        Full access inside their company.

    MANAGER:
        Access restricted to their branch/project scope.

    EMPLOYEE:
        Access restricted to resources they participate in.

    INDIVIDUAL:
        Personal resources only.
    """

    @staticmethod
    def users(user):
        if user.role == Roles.SUPERUSER:
            return User.objects.filter(is_deleted=False)

        if user.role == Roles.ADMIN:
            return User.objects.filter(
                company=user.company,
                is_deleted=False,
            )

        if user.role == Roles.MANAGER:
            return User.objects.filter(
                company=user.company,
                branch=user.branch,
                is_deleted=False,
            )

        return User.objects.filter(
            pk=user.pk,
            is_deleted=False,
        )

    @staticmethod
    def companies(user):
        if user.role == Roles.SUPERUSER:
            return Company.objects.all()

        if user.company_id:
            return Company.objects.filter(
                pk=user.company_id,
                is_active=True,
            )

        return Company.objects.none()

    @staticmethod
    def branches(user):
        if user.role == Roles.SUPERUSER:
            return Branch.objects.all()

        if not user.company_id:
            return Branch.objects.none()

        queryset = Branch.objects.filter(
            company_id=user.company_id,
            is_active=True,
        )

        if user.role in (Roles.MANAGER, Roles.EMPLOYEE):
            if not user.branch_id:
                return Branch.objects.none()

            queryset = queryset.filter(pk=user.branch_id)

        return queryset

    @staticmethod
    def projects(user):
        if user.role == Roles.SUPERUSER:
            return Project.objects.filter(is_active=True)

        if not user.company_id:
            return Project.objects.none()

        if user.role == Roles.ADMIN:
            return Project.objects.filter(
                company_id=user.company_id,
                is_active=True,
            )

        if user.role == Roles.MANAGER:
            if not user.branch_id:
                return Project.objects.none()

            return Project.objects.filter(
                company_id=user.company_id,
                branches=user.branch_id,
                is_active=True,
            ).distinct()

        if user.role == Roles.EMPLOYEE:
            return Project.objects.filter(
                company_id=user.company_id,
                memberships__user=user,
                is_active=True,
            ).distinct()

        return Project.objects.none()

    @staticmethod
    def project_memberships(user):
        if user.role == Roles.SUPERUSER:
            return ProjectMembership.objects.all()

        if not user.company_id:
            return ProjectMembership.objects.none()

        if user.role == Roles.ADMIN:
            return ProjectMembership.objects.filter(
                project__company_id=user.company_id,
            )

        if user.role == Roles.MANAGER:
            if not user.branch_id:
                return ProjectMembership.objects.none()

            return ProjectMembership.objects.filter(
                project__company_id=user.company_id,
                project__branches=user.branch_id,
            ).distinct()

        return ProjectMembership.objects.filter(
            user=user,
            project__company_id=user.company_id,
        ).distinct()

    @staticmethod
    def tasks(user):
        if user.role == Roles.SUPERUSER:
            return Task.objects.filter(is_active=True)

        if not user.company_id:
            return Task.objects.none()

        if user.role == Roles.ADMIN:
            return Task.objects.filter(
                company_id=user.company_id,
                is_active=True,
            )

        if user.role == Roles.MANAGER:
            if not user.branch_id:
                return Task.objects.none()

            return Task.objects.filter(
                company_id=user.company_id,
                project__branches=user.branch_id,
                is_active=True,
            ).distinct()

        if user.role == Roles.EMPLOYEE:
            return Task.objects.filter(
                company_id=user.company_id,
                project__memberships__user=user,
                assignees=user,
                is_active=True,
            ).distinct()

        return Task.objects.none()

    @staticmethod
    def reports(user):
        if user.role == Roles.SUPERUSER:
            return Report.objects.all()

        if not user.company_id:
            return Report.objects.none()

        if user.role == Roles.ADMIN:
            return Report.objects.filter(
                company_id=user.company_id,
            )

        if user.role == Roles.MANAGER:
            return Report.objects.filter(
                company_id=user.company_id,
                branch_id=user.branch_id,
            )

        if user.role == Roles.EMPLOYEE:
            return Report.objects.filter(
                company_id=user.company_id,
                created_by=user,
            )

        return Report.objects.none()

    @staticmethod
    def comments(user):
        if user.role == Roles.SUPERUSER:
            return ReportComment.objects.all()

        if not user.company_id:
            return ReportComment.objects.none()

        if user.role == Roles.ADMIN:
            return ReportComment.objects.filter(
                report__company_id=user.company_id,
            )

        if user.role == Roles.MANAGER:
            return ReportComment.objects.filter(
                report__company_id=user.company_id,
                report__branch_id=user.branch_id,
            )

        return ReportComment.objects.filter(
            report__company_id=user.company_id,
            author=user,
        )

    @staticmethod
    def notifications(user):
        if user.role == Roles.SUPERUSER:
            return Notification.objects.filter(recipient=user)

        return Notification.objects.filter(
            recipient=user,
            company_id=user.company_id,
        )

    @staticmethod
    def activity(user):
        if user.role == Roles.SUPERUSER:
            return ActivityLog.objects.all()

        return ActivityLog.objects.filter(
            company_id=user.company_id,
        )

    @staticmethod
    def invites(user):
        if user.role == Roles.SUPERUSER:
            return CompanyInvite.objects.all()

        if not user.company_id:
            return CompanyInvite.objects.none()

        return CompanyInvite.objects.filter(
            company_id=user.company_id,
        )

    @staticmethod
    def subscriptions(user):
        if user.role == Roles.SUPERUSER:
            return Subscription.objects.all()

        if not user.company_id:
            return Subscription.objects.none()

        return Subscription.objects.filter(
            company_id=user.company_id,
        )

    @staticmethod
    def analytics_snapshots(user):
        if user.role == Roles.SUPERUSER:
            return AnalyticsSnapshot.objects.all()

        if not user.company_id:
            return AnalyticsSnapshot.objects.none()

        return AnalyticsSnapshot.objects.filter(
            company_id=user.company_id,
        )

    @staticmethod
    def ai_insights(user):
        if user.role == Roles.SUPERUSER:
            return AIInsight.objects.all()

        if not user.company_id:
            return AIInsight.objects.none()

        return AIInsight.objects.filter(
            company_id=user.company_id,
        )
    

    @staticmethod
    def filter(queryset, user):
        if user.role == Roles.SUPERUSER:
            return queryset
    
        model = queryset.model
    
        if hasattr(model, "company_id"):
            if not user.company_id:
                return queryset.none()
    
            queryset = queryset.filter(
                company_id=user.company_id
            )
    
        if hasattr(model, "branch_id"):
            if user.role == Roles.MANAGER:
                if not user.branch_id:
                    return queryset.none()
    
                queryset = queryset.filter(
                    branch_id=user.branch_id
                )
    
            elif user.role == Roles.EMPLOYEE:
                queryset = queryset.filter(
                    branch_id=user.branch_id
                )
    
        return queryset
    

# from users.models import User
# from companies.models import Company, Branch
# from projects.models import Project, ProjectMembership
# from tasks.models import Task
# from reports.models import Report, ReportComment
# from notifications.models import Notification
# from activity.models import ActivityLog

# from core.roles import Roles


# class TenantService:
#     """
#     Centralized tenant isolation.

#     Every queryset in the system should pass here.

#     Never filter company/branch directly inside ViewSets.
#     """

#     @staticmethod
#     def filter(queryset, user):
#         """Generic fallback for models with company/branch fields."""
#         if user.role == Roles.SUPERUSER:
#             return queryset
#         if hasattr(queryset.model, "company"):
#             queryset = queryset.filter(company=user.company)
#         if hasattr(queryset.model, "branch") and user.role in (Roles.MANAGER, Roles.EMPLOYEE):
#             queryset = queryset.filter(branch=user.branch)
#         return queryset

#     # -----------------------------
#     # USERS
#     # -----------------------------
#     @staticmethod
#     def users(user):
#         if user.role == Roles.SUPERUSER:
#             return User.objects.all()
#         if user.role == Roles.ADMIN:
#             # Company admin sees all users in their company (all branches)
#             return User.objects.filter(company=user.company)
#         if user.role == Roles.MANAGER:
#             # Branch manager sees all users in their branch
#             return User.objects.filter(company=user.company, branch=user.branch)
#         if user.role == Roles.EMPLOYEE:
#             # Employees only see themselves
#             return User.objects.filter(id=user.id)
#         return User.objects.filter(id=user.id)

#     # -----------------------------
#     # COMPANIES
#     # -----------------------------
#     @staticmethod
#     def companies(user):
#         if user.role == Roles.SUPERUSER:
#             return Company.objects.all()
#         if user.company:
#             return Company.objects.filter(id=user.company.id)
#         return Company.objects.none()

#     # -----------------------------
#     # BRANCHES
#     # -----------------------------
#     @staticmethod
#     def branches(user):
#         if user.role == Roles.SUPERUSER:
#             return Branch.objects.all()
#         if user.role == Roles.ADMIN:
#             # Company admin sees all branches in their company
#             return Branch.objects.filter(company=user.company)
#         if user.role == Roles.MANAGER:
#             # Branch manager sees only their branch
#             return Branch.objects.filter(id=user.branch.id)
#         if user.role == Roles.EMPLOYEE:
#             return Branch.objects.filter(id=user.branch.id)
#         return Branch.objects.none()

#     # -----------------------------
#     # PROJECTS
#     # -----------------------------
#     @staticmethod
#     def projects(user):
#         if user.role == Roles.SUPERUSER:
#             return Project.objects.filter(is_active=True)
#         if user.role == Roles.ADMIN:
#             # Company admin sees all projects in their company
#             return Project.objects.filter(company=user.company, is_active=True)
#         if user.role == Roles.MANAGER:
#             # Branch manager sees all projects in their branch
#             return Project.objects.filter(
#                 company=user.company,
#                 branches=user.branch,
#                 is_active=True
#             ).distinct()
#         if user.role == Roles.EMPLOYEE:
#             # Employees see only projects they are members of
#             return Project.objects.filter(memberships__user=user, is_active=True).distinct()
#         return Project.objects.none()

#     # -----------------------------
#     # PROJECT MEMBERSHIPS
#     # -----------------------------
#     @staticmethod
#     def project_memberships(user):
#         if user.role == Roles.SUPERUSER:
#             return ProjectMembership.objects.all()
#         if user.role == Roles.ADMIN:
#             return ProjectMembership.objects.filter(project__company=user.company)
#         if user.role == Roles.MANAGER:
#             return ProjectMembership.objects.filter(project__branches=user.branch)
#         return ProjectMembership.objects.filter(user=user).distinct()

#     # -----------------------------
#     # TASKS
#     # -----------------------------
#     @staticmethod
#     def tasks(user):
#         if user.role == Roles.SUPERUSER:
#             return Task.objects.filter(is_active=True)
#         if user.role == Roles.ADMIN:
#             return Task.objects.filter(project__company=user.company, is_active=True).distinct()
#         if user.role == Roles.MANAGER:
#             return Task.objects.filter(
#                 project__company=user.company,
#                 project__branches=user.branch,
#                 is_active=True
#             ).distinct()
#         if user.role == Roles.EMPLOYEE:
#             return Task.objects.filter(project__memberships__user=user, is_active=True).distinct()
#         return Task.objects.none()

#     # -----------------------------
#     # REPORTS
#     # -----------------------------
#     @staticmethod
#     def reports(user):
#         if user.role == Roles.SUPERUSER:
#             return Report.objects.all()
#         if user.role == Roles.ADMIN:
#             return Report.objects.filter(company=user.company)
#         if user.role == Roles.MANAGER:
#             return Report.objects.filter(company=user.company, branch=user.branch)
#         if user.role == Roles.EMPLOYEE:
#             return Report.objects.filter(company=user.company, branch=user.branch)
#         return Report.objects.none()

#     # -----------------------------
#     # COMMENTS
#     # -----------------------------
#     @staticmethod
#     def comments(user):
#         if user.role == Roles.SUPERUSER:
#             return ReportComment.objects.all()
#         return ReportComment.objects.filter(report__company=user.company)

#     # -----------------------------
#     # NOTIFICATIONS
#     # -----------------------------
#     @staticmethod
#     def notifications(user):
#         if user.role == Roles.SUPERUSER:
#             return Notification.objects.all()
#         return Notification.objects.filter(recipient=user)

#     # -----------------------------
#     # ACTIVITY LOGS
#     # -----------------------------
#     @staticmethod
#     def activity(user):
#         if user.role == Roles.SUPERUSER:
#             return ActivityLog.objects.all()
#         return ActivityLog.objects.filter(company=user.company)
