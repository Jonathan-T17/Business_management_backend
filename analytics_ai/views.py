from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from analytics_ai.permissions import IsCompanyAdmin
from subscriptions.permissions import HasActiveSubscription
from analytics_ai.models import AnalyticsSnapshot
from analytics_ai.serializers import AnalyticsSnapshotSerializer


class CompanyAnalyticsView(APIView):

    permission_classes = [
        IsAuthenticated,
        HasActiveSubscription,
        IsCompanyAdmin,
    ]

    def get(self, request):
        snapshots = AnalyticsSnapshot.objects.filter(
            company=request.user.company,
            snapshot_type="company"
        )[:10]

        serializer = AnalyticsSnapshotSerializer(snapshots, many=True)
        return Response(serializer.data)