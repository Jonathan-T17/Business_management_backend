from django.urls import path
from .views import (
    SetupFinishView, SetupHealthView, SetupStatusView,
    SetupStepCompleteView, SetupStepSkipView,
)

urlpatterns = [
    path("status/", SetupStatusView.as_view(), name="company-setup-status"),
    path("health/", SetupHealthView.as_view(), name="company-setup-health"),
    path("steps/complete/", SetupStepCompleteView.as_view(), name="company-setup-step-complete"),
    path("steps/skip/", SetupStepSkipView.as_view(), name="company-setup-step-skip"),
    path("finish/", SetupFinishView.as_view(), name="company-setup-finish"),
]

# Merge the existing configuration routers from urls_legacy_reference.py during
# integration. Their ViewSets remain useful after replacing their permission
# and service layers with the Phase 8 policy.
