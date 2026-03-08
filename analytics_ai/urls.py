from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AIInsightViewSet, CompanyAnalyticsView

router = DefaultRouter()
router.register("ai-insights", AIInsightViewSet, basename="ai-insights")

urlpatterns = [
    path(
        "company/",
        CompanyAnalyticsView.as_view(),
        name="company-analytics"
    ),
]

urlpatterns += router.urls