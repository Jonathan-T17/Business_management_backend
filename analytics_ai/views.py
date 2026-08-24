from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView, PermissionDenied
from rest_framework.decorators import action

from companies.models import Branch
from core.roles import Roles
from projects.models import Project

from subscriptions.permissions import HasActiveSubscription
from security.viewsets import SecureModelViewSet
from subscriptions.services import SubscriptionService

from .models import (
    AnalyticsSnapshot,
    AIInsight,
    AIAnalyticsRecord,
)

from .serializers import (
    AnalyticsSnapshotSerializer,
    AIInsightSerializer,
    AIAnalyticsRecordSerializer,
)

from .permissions import IsAnalyticsAdmin

from .services import (
    generate_company_metrics,
    generate_branch_metrics,
    generate_project_metrics,
)

from .insight_engine import (
    generate_company_insights,
    generate_project_summary,
    generate_branch_summary,
)


class CompanyAnalyticsView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def get(self, request):
        user = request.user

        if (
            request.user.role != Roles.SUPERUSER
            and not SubscriptionService.ai_enabled(
                request.user.company
            )
        ):
            raise PermissionDenied(
                "AI analytics are not included in your current subscription."
            )
        
        project_id = request.query_params.get("project_id")
        branch_id = request.query_params.get("branch_id")

        if user.role == Roles.SUPERUSER:
            company_id = request.query_params.get("company_id")

            if company_id:
                from companies.models import Company

                company = Company.objects.filter(
                    id=company_id,
                    is_active=True,
                ).first()

                if not company:
                    return Response(
                        {"detail": "Company not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                company = user.company

        else:
            company = user.company

        if not company:
            return Response(
                {"detail": "User is not associated with a company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        snapshots = AnalyticsSnapshot.objects.filter(
            company=company
        )

        insights = AIInsight.objects.filter(
            company=company,
            status="ACTIVE",
        )

        if project_id:
            project = Project.objects.filter(
                id=project_id,
                company=company,
            ).first()

            if not project:
                return Response(
                    {"detail": "Project not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            snapshots = snapshots.filter(
                project=project,
                snapshot_type="project",
            )

            insights = insights.filter(
                project=project
            )

        elif branch_id:
            branch = Branch.objects.filter(
                id=branch_id,
                company=company,
            ).first()

            if not branch:
                return Response(
                    {"detail": "Branch not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            snapshots = snapshots.filter(
                branch=branch,
                snapshot_type="branch",
            )

            insights = insights.filter(
                branch=branch
            )

        else:
            snapshots = snapshots.filter(
                snapshot_type="company",
                branch__isnull=True,
                project__isnull=True,
            )

            insights = insights.filter(
                branch__isnull=True,
                project__isnull=True,
            )

        snapshots = snapshots.order_by(
            "-generated_at"
        )[:10]

        insights = insights.order_by(
            "-generated_at"
        )[:10]

        return Response({
            "company_id": company.id,
            "snapshots": AnalyticsSnapshotSerializer(
                snapshots,
                many=True,
            ).data,
            "insights": AIInsightSerializer(
                insights,
                many=True,
            ).data,
        })


class AnalyticsSnapshotViewSet(
    viewsets.ReadOnlyModelViewSet
):
    serializer_class = AnalyticsSnapshotSerializer

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def get_queryset(self):
        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return AnalyticsSnapshot.objects.all()

        return AnalyticsSnapshot.objects.filter(
            company=user.company
        )


class AIInsightViewSet(
    SecureModelViewSet
):
    serializer_class = AIInsightSerializer

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    audit_action = "AI_INSIGHT"

    def get_queryset(self):
        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return AIInsight.objects.all()

        return AIInsight.objects.filter(
            company=user.company
        )

    @action(
        detail=True,
        methods=["post"],
    )
    def resolve(self, request, pk=None):
        insight = self.get_object()

        insight.resolve()

        return Response(
            AIInsightSerializer(insight).data
        )


class AIAnalyticsRecordViewSet(
    viewsets.ReadOnlyModelViewSet
):
    serializer_class = AIAnalyticsRecordSerializer

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def get_queryset(self):
        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return AIAnalyticsRecord.objects.all()

        return AIAnalyticsRecord.objects.filter(
            company=user.company
        )


class GenerateCompanyAnalyticsView(APIView):
    """
    Generate a fresh company analytics snapshot and insights.
    """

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def post(self, request):
        company = request.user.company

        if not company:
            return Response(
                {"detail": "User has no company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metrics = generate_company_metrics(company)

        snapshot = AnalyticsSnapshot.objects.create(
            company=company,
            snapshot_type="company",
            total_tasks=metrics["total_tasks"],
            completed_tasks=metrics["completed_tasks"],
            pending_tasks=metrics["pending_tasks"],
            in_progress_tasks=metrics["in_progress_tasks"],
            blocked_tasks=metrics["blocked_tasks"],
            overdue_tasks=metrics["overdue_tasks"],
            total_projects=metrics["total_projects"],
            active_projects=metrics["active_projects"],
            total_reports=metrics["total_reports"],
            total_comments=metrics["total_comments"],
            completion_rate=metrics["completion_rate"],
            overdue_rate=metrics["overdue_rate"],
            workload_balance_score=metrics[
                "workload_balance_score"
            ],
        )

        insights = generate_company_insights(
            company
        )

        return Response(
            {
                "snapshot": AnalyticsSnapshotSerializer(
                    snapshot
                ).data,
                "insights": AIInsightSerializer(
                    insights,
                    many=True,
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class GenerateProjectAnalyticsView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def post(self, request, project_id):
        project = Project.objects.filter(
            id=project_id,
            company=request.user.company,
            is_active=True,
        ).first()

        if not project:
            return Response(
                {"detail": "Project not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        metrics = generate_project_metrics(project)

        snapshot = AnalyticsSnapshot.objects.create(
            company=project.company,
            project=project,
            snapshot_type="project",
            total_tasks=metrics["total_tasks"],
            completed_tasks=metrics["completed_tasks"],
            pending_tasks=metrics["pending_tasks"],
            in_progress_tasks=metrics["in_progress_tasks"],
            blocked_tasks=metrics["blocked_tasks"],
            overdue_tasks=metrics["overdue_tasks"],
            total_reports=metrics["total_reports"],
            total_comments=metrics["total_comments"],
            completion_rate=metrics["completion_rate"],
            overdue_rate=metrics["overdue_rate"],
            collaboration_score=metrics[
                "collaboration_score"
            ],
        )

        insight = generate_project_summary(
            project
        )

        return Response(
            {
                "snapshot": AnalyticsSnapshotSerializer(
                    snapshot
                ).data,
                "insight": AIInsightSerializer(
                    insight
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class GenerateBranchAnalyticsView(APIView):

    permission_classes = [
        IsAuthenticated,
        IsAnalyticsAdmin,
        HasActiveSubscription,
    ]

    def post(self, request, branch_id):
        branch = Branch.objects.filter(
            id=branch_id,
            company=request.user.company,
            is_active=True,
        ).first()

        if not branch:
            return Response(
                {"detail": "Branch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        metrics = generate_branch_metrics(
            branch
        )

        snapshot = AnalyticsSnapshot.objects.create(
            company=branch.company,
            branch=branch,
            snapshot_type="branch",
            total_tasks=metrics["total_tasks"],
            completed_tasks=metrics["completed_tasks"],
            pending_tasks=metrics["pending_tasks"],
            in_progress_tasks=metrics["in_progress_tasks"],
            blocked_tasks=metrics["blocked_tasks"],
            overdue_tasks=metrics["overdue_tasks"],
            total_projects=metrics["total_projects"],
            active_projects=metrics["active_projects"],
            total_reports=metrics["total_reports"],
            total_comments=metrics["total_comments"],
            completion_rate=metrics["completion_rate"],
            overdue_rate=metrics["overdue_rate"],
        )

        insight = generate_branch_summary(
            branch
        )

        return Response(
            {
                "snapshot": AnalyticsSnapshotSerializer(
                    snapshot
                ).data,
                "insight": AIInsightSerializer(
                    insight
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )