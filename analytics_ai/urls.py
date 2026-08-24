from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyAnalyticsView,
    AnalyticsSnapshotViewSet,
    AIInsightViewSet,
    AIAnalyticsRecordViewSet,
    GenerateCompanyAnalyticsView,
    GenerateProjectAnalyticsView,
    GenerateBranchAnalyticsView,
)


router = DefaultRouter()

router.register(
    "snapshots",
    AnalyticsSnapshotViewSet,
    basename="analytics-snapshots",
)

router.register(
    "ai-insights",
    AIInsightViewSet,
    basename="ai-insights",
)

router.register(
    "records",
    AIAnalyticsRecordViewSet,
    basename="analytics-records",
)


urlpatterns = [
    path(
        "company/",
        CompanyAnalyticsView.as_view(),
        name="company-analytics",
    ),

    path(
        "generate/company/",
        GenerateCompanyAnalyticsView.as_view(),
        name="generate-company-analytics",
    ),

    path(
        "generate/project/<int:project_id>/",
        GenerateProjectAnalyticsView.as_view(),
        name="generate-project-analytics",
    ),

    path(
        "generate/branch/<int:branch_id>/",
        GenerateBranchAnalyticsView.as_view(),
        name="generate-branch-analytics",
    ),
]

urlpatterns += router.urls