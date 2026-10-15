from django.db.models import Q
from django.conf import settings

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from core.audit import ActivityAudit
from core.roles import Roles
from core.visibility import VisibilityService

from security.viewsets import SecureModelViewSet

from notifications.services import CommunicationService, create_notification

from projects.models import ProjectMembership
from subscriptions.services import SubscriptionService
from users.models import User

from rest_framework.exceptions import ValidationError

from workflows.models import WorkflowDefinition
from workflows.services import WorkflowService

from .models import Report, ReportComment
from .serializers import (
    ReportSerializer,
    ReportCommentSerializer,
)
from .permissions import CanViewReport


# ============================================================
# Report ViewSet
# ============================================================

class ReportViewSet(SecureModelViewSet):

    queryset = Report.objects.all()

    serializer_class = ReportSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    audit_action = "REPORT"

    def get_queryset(self):

        # Enforce subscription feature flag
        if (
            self.request.user.role != Roles.SUPERUSER
            and not SubscriptionService.reports_enabled(self.request.user.company)
        ):
            raise PermissionDenied(
                "Reports are not included in your current subscription."
            )
        return (
            VisibilityService
            .reports_queryset(
                user=self.request.user,
                queryset=self.queryset,
            )
            .select_related(
                "created_by",
                "company",
                "branch",
                "project",
                "task",
            )
            .prefetch_related(
                "fields",
                "comments",
            )
            .distinct()
        )

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):

        # Enforce subscription feature flag
        if (
            self.request.user.role != Roles.SUPERUSER
            and not SubscriptionService.reports_enabled(self.request.user.company)
        ):
            raise PermissionDenied(
                "Reports are not included in your current subscription."
            )

        report = serializer.save(
            created_by=self.request.user,
            company=self.request.user.company,
        )

        ActivityAudit.log(
            user=self.request.user,
            company=report.company,
            project=report.project,
            task=report.task,
            action="REPORT_CREATED",
            metadata={
                "object_type": "Report",
                "object_id": str(report.id),
                "type": report.report_type,
                "title": report.title,
            },
        )





    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    @staticmethod
    def _critical_notification_recipients(report):
        candidates = list(User.objects.filter(
            company=report.company, role="ADMIN", is_active=True, is_deleted=False,
        ))
        branch_manager = getattr(report.branch, "manager", None) if report.branch else None
        if branch_manager:
            candidates.append(branch_manager)
        return list({user.pk: user for user in candidates if (
            user.is_active and not user.is_deleted
            and user.company_id == report.company_id
            and VisibilityService.can_view_report(user, report)
        )}.values())

    def perform_update(self, serializer):
        report = serializer.save()
    
        ActivityAudit.log(
            user=self.request.user,
            company=report.company,
            project=report.project,
            task=report.task,
            action="REPORT_UPDATED",
            metadata={
                "object_type": "Report",
                "object_id": str(report.id),
                "title": report.title,
            },
        )
    
        # Escalate updates for critical report types
        if report.report_type in ("INCIDENT", "REQUEST"):
            for recipient in self._critical_notification_recipients(report):
                CommunicationService.send(
                    recipient=recipient,
                    company=report.company,
                    notification_type="REPORT_UPDATED",
                    title="Report Updated",
                    message=f"'{report.title}' was updated.",
                    reference_id=str(report.id),
                    url=f"/reports/{report.id}",
                    send_email=True,
                    email_subject=f"{report.report_type.title()} report updated",
                    email_template="emails/report_notification.html",
                    email_context={
                        "report": report,
                        "action_url": f"{settings.FRONTEND_URL}/reports/{report.id}",
                    },
                )


    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    def perform_destroy(self, instance):
        # Resolve visibility before deletion removes workflow participation.
        report_id = str(instance.pk)
        recipients = self._critical_notification_recipients(instance) if instance.report_type in ("INCIDENT", "REQUEST") else []
        ActivityAudit.log(
            user=self.request.user,
            company=instance.company,
            project=instance.project,
            task=instance.task,
            action="REPORT_DELETED",
            metadata={
                "object_type": "Report",
                "object_id": str(instance.id),
                "title": instance.title,
            },
        )
    
        instance.delete()
    
        # Escalate deletion for critical report types
        if instance.report_type in ("INCIDENT", "REQUEST"):
            for recipient in recipients:
                CommunicationService.send(
                    recipient=recipient,
                    company=instance.company,
                    notification_type="REPORT_DELETED",
                    title="Report Deleted",
                    message=f"'{instance.title}' was deleted.",
                    reference_id=report_id,
                    url="/reports",
                    send_email=True,
                    email_subject=f"{instance.report_type.title()} report deleted",
                    email_template="emails/report_notification.html",
                    email_context={
                        "report": instance,
                        "action_url": f"{settings.FRONTEND_URL}/reports",
                    },
                )
    

    # --------------------------------------------------------
    # Company Feed
    # --------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="company-feed",
    )
    def company_feed(self, request):

        reports = (
            VisibilityService
            .reports(request.user)
            .select_related(
                "created_by",
                "branch",
                "project",
                "task",
            )
            .prefetch_related(
                "fields",
                "comments",
            )
            .order_by("-created_at")[:20]
        )

        serializer = self.get_serializer(
            reports,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # Project Feed
    # --------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="project/(?P<project_id>[^/.]+)",
    )
    def project_reports(
        self,
        request,
        project_id=None,
    ):

        reports = self.get_queryset().filter(
            project_id=project_id,
            visibility="PROJECT",
        )

        serializer = self.get_serializer(
            reports,
            many=True,
        )

        return Response(serializer.data)

    # --------------------------------------------------------
    # My Reports
    # --------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="mine",
    )
    def my_reports(self, request):

        reports = self.get_queryset().filter(
            created_by=request.user
        )

        serializer = self.get_serializer(
            reports,
            many=True,
        )

        return Response(serializer.data)

    # --------------------------------------------------------
    # Notification helper
    # --------------------------------------------------------

    def _notify_report_submitted(self, report):

        if not report.project or report.status in ("DRAFT", "RETURNED"):
            return

        memberships = (
            ProjectMembership.objects
            .filter(project=report.project, user__company=report.company, user__is_active=True, user__is_deleted=False)
            .exclude(user=self.request.user)
            .select_related("user")
        )

        for membership in memberships:
            if not VisibilityService.can_view_report(membership.user, report):
                continue

            create_notification(
                recipient=membership.user,
                company=report.company,
                notification_type="REPORT_SUBMITTED",
                title="New Report Submitted",
                message=(
                    f"A new report '{report.title}' "
                    f"was submitted in project "
                    f"'{report.project.name}'."
                ),
                reference_id=str(report.id),
            )




    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(
        self,
        request,
        pk=None,
    ):
    
        report = self.get_object()
    
        if report.created_by != request.user:
            raise ValidationError(
                "Only the report author can submit this report."
            )
    
        if report.status not in (
            "DRAFT",
            "RETURNED",
        ):
            raise ValidationError(
                "This report cannot be submitted in its current status."
            )
    
        workflow_id = request.data.get(
            "workflow"
        )
    
        if not workflow_id:
            raise ValidationError({
                "workflow":
                    "Workflow is required."
            })
    
        try:
            workflow = (
                WorkflowDefinition.objects.get(
                    id=workflow_id,
                    company=report.company,
                    target_type="REPORT",
                    is_active=True,
                )
            )
    
        except WorkflowDefinition.DoesNotExist:
    
            raise ValidationError({
                "workflow":
                    "Invalid report workflow."
            })
    
        instance = WorkflowService.start(
            workflow=workflow,
            target=report,
            submitted_by=request.user,
            request=request,
        )
    
        report.refresh_from_db()
        self._notify_report_submitted(report)
    
        return Response(
            {
                "message":
                    "Report submitted successfully.",
    
                "report_id":
                    str(report.id),
    
                "report_status":
                    report.status,
    
                "workflow_instance":
                    instance.id,
            },
            status=
                status.HTTP_200_OK,
        )


# ============================================================
# Report Comment ViewSet
# ============================================================

class ReportCommentViewSet(SecureModelViewSet):

    queryset = ReportComment.objects.all()

    serializer_class = ReportCommentSerializer

    permission_classes = [
        IsAuthenticated,
    ]

    audit_action = "REPORT_COMMENT"

    def get_queryset(self):

        user = self.request.user

        reports = VisibilityService.reports(user)

        return (
            ReportComment.objects
            .filter(report__in=reports)
            .select_related(
                "report",
                "report__company",
                "report__project",
                "report__task",
                "author",
            )
            .order_by("created_at")
        )

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):

        report = serializer.validated_data["report"]

        if not VisibilityService.can_view_report(
            self.request.user,
            report,
        ):
            raise PermissionDenied(
                "You do not have permission to comment on this report."
            )

        comment = serializer.save(
            author=self.request.user,
        )

        ActivityAudit.log(
            user=self.request.user,
            company=report.company,
            project=report.project,
            task=report.task,
            action="REPORT_COMMENT_ADDED",
            metadata={
                "object_type": "ReportComment",
                "object_id": str(comment.id),
                "report_id": str(report.id),
            },
        )

        self._notify_comment(comment)


    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):

        comment = self.get_object()

        # Only the author or an administrator should edit
        # a comment.

        if (
            comment.author_id != self.request.user.id
            and not self._is_admin()
        ):
            raise PermissionDenied(
                "You cannot edit this comment."
            )

        comment = serializer.save()

        ActivityAudit.log(
            user=self.request.user,
            company=comment.report.company,
            project=comment.report.project,
            task=comment.report.task,
            action="REPORT_COMMENT_UPDATED",
            metadata={
                "object_type": "ReportComment",
                "object_id": str(comment.id),
            },
        )

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    def perform_destroy(self, instance):

        if (
            instance.author_id != self.request.user.id
            and not self._is_admin()
        ):
            raise PermissionDenied(
                "You cannot delete this comment."
            )

        ActivityAudit.log(
            user=self.request.user,
            company=instance.report.company,
            project=instance.report.project,
            task=instance.report.task,
            action="REPORT_COMMENT_DELETED",
            metadata={
                "object_type": "ReportComment",
                "object_id": str(instance.id),
            },
        )

        instance.delete()

    # --------------------------------------------------------
    # Admin helper
    # --------------------------------------------------------

    def _is_admin(self):

        return getattr(
            self.request.user,
            "is_staff",
            False,
        )

    # --------------------------------------------------------
    # Notifications
    # --------------------------------------------------------

    def _notify_comment(self, comment):

        report = comment.report

        recipients = set()

        # Original report author
        if (
            report.created_by
            and report.created_by_id != self.request.user.id
        ):
            recipients.add(report.created_by_id)

        # Project members
        if report.project:

            memberships = (
                ProjectMembership.objects
                .filter(
                    project=report.project
                )
                .exclude(
                    user=self.request.user
                )
                .select_related("user")
            )

            for membership in memberships:
                recipients.add(
                    membership.user_id
                )

        users = (
            report.company.users
            .filter(id__in=recipients, is_active=True, is_deleted=False)
        )

        for user in users:
            if not VisibilityService.can_view_report(user, report):
                continue

            create_notification(
                recipient=user,
                company=report.company,
                notification_type="REPORT_COMMENT",
                title="New Report Comment",
                message=(
                    f"A new comment was added to "
                    f"report '{report.title}'."
                ),
                reference_id=str(report.id),
            )
