from django.urls import path
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
)


router = DefaultRouter()


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
]


urlpatterns += router.urls