from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

from analytics_ai.permissions import IsCompanyAdmin
from subscriptions.permissions import HasActiveSubscription
from analytics_ai.models import AnalyticsSnapshot, AIInsight
from analytics_ai.serializers import AnalyticsSnapshotSerializer, AIInsightSerializer


class CompanyAnalyticsView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasActiveSubscription,
        IsCompanyAdmin,
    ]

    def get(self, request):
        project_id = request.query_params.get("project_id")
        branch_id = request.query_params.get("branch_id")

        if project_id:
            snapshots = AnalyticsSnapshot.objects.filter(
                company=request.user.company,
                project_id=project_id,
                snapshot_type="project"
            ).order_by("-generated_at")[:10]

            insights = AIInsight.objects.filter(
                company=request.user.company,
                project_id=project_id
            ).order_by("-generated_at")[:10]

        elif branch_id:
            snapshots = AnalyticsSnapshot.objects.filter(
                company=request.user.company,
                branch_id=branch_id,
                snapshot_type="branch"
            ).order_by("-generated_at")[:10]

            insights = AIInsight.objects.filter(
                company=request.user.company,
                project__isnull=True  # adjust if branch-specific insights exist
            ).order_by("-generated_at")[:10]

        else:
            snapshots = AnalyticsSnapshot.objects.filter(
                company=request.user.company,
                snapshot_type="company"
            ).order_by("-generated_at")[:10]

            insights = AIInsight.objects.filter(
                company=request.user.company,
                project__isnull=True
            ).order_by("-generated_at")[:10]

        snapshot_serializer = AnalyticsSnapshotSerializer(snapshots, many=True)
        insight_serializer = AIInsightSerializer(insights, many=True)

        return Response({
            "snapshots": snapshot_serializer.data,
            "insights": insight_serializer.data
        })


class AIInsightViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for AIInsights.
    """
    serializer_class = AIInsightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIInsight.objects.filter(
            company=self.request.user.company
        )