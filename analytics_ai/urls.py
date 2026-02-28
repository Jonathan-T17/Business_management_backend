from django.urls import path
from .views import CompanyAnalyticsView

urlpatterns = [
    path(
        "analytics/company/",
        CompanyAnalyticsView.as_view(),
        name="company-analytics"
    ),
]