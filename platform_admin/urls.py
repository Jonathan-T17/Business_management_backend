from django.urls import path
from .maintenance import MaintenanceCatalogue, MaintenanceRecords, MaintenanceChoices
from rest_framework.routers import DefaultRouter

from .views import (
    PlatformDashboardView,
    PlatformCompanyViewSet,
    PlatformEmailDeliveryViewSet,
    PlatformUserViewSet,
    PlatformActiveSessionViewSet,
    PlatformLoginHistoryViewSet,
    PlatformFailedLoginViewSet,
    PlatformAuditLogViewSet,
    PlatformSubscriptionViewSet,
    PlatformActivityViewSet,
    PlatformHealthView,
    PlatformSettingsView,
    PlatformPlanViewSet,
)


router = DefaultRouter()
from support.views import PlatformSupportTicketViewSet
router.register("support/tickets", PlatformSupportTicketViewSet, basename="platform-support")
router.register("plans", PlatformPlanViewSet, basename="platform-plans")


router.register(
    "companies",
    PlatformCompanyViewSet,
    basename="platform-companies",
)

router.register(
    "users",
    PlatformUserViewSet,
    basename="platform-users",
)

router.register(
    "security/sessions",
    PlatformActiveSessionViewSet,
    basename="platform-sessions",
)

router.register(
    "sessions",
    PlatformActiveSessionViewSet,
    basename="platform-sessions-short",
)

router.register(
    "security/login-history",
    PlatformLoginHistoryViewSet,
    basename="platform-login-history",
)

router.register(
    "security/failed-logins",
    PlatformFailedLoginViewSet,
    basename="platform-failed-logins",
)

router.register(
    "audit",
    PlatformAuditLogViewSet,
    basename="platform-audit",
)

router.register(
    "subscriptions",
    PlatformSubscriptionViewSet,
    basename="platform-subscriptions",
)

router.register(
    "activity",
    PlatformActivityViewSet,
    basename="platform-activity",
)

router.register(
    "communications/emails",
    PlatformEmailDeliveryViewSet,
    basename=
        "platform-email-delivery",
)


urlpatterns = [
    path("administration/", MaintenanceCatalogue.as_view()),
    path("administration/<slug:key>/", MaintenanceRecords.as_view()),
    path("administration/<slug:key>/choices/<str:field>/", MaintenanceChoices.as_view()),
    path("administration/<slug:key>/<str:pk>/", MaintenanceRecords.as_view()),
    path(
        "dashboard/",
        PlatformDashboardView.as_view(),
        name="platform-dashboard",
    ),

    path(
        "health/",
        PlatformHealthView.as_view(),
        name="platform-health",
    ),

    path(
        "settings/",
        PlatformSettingsView.as_view(),
        name="platform-settings",
    ),
]


urlpatterns += router.urls
