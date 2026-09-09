from rest_framework.routers import DefaultRouter

from .views import (
    ReportingScheduleViewSet,
    ReportingObligationViewSet,
)

router = DefaultRouter()

router.register(
    "reporting-schedules",
    ReportingScheduleViewSet,
    basename="reporting-schedule",
)

router.register(
    "reporting-obligations",
    ReportingObligationViewSet,
    basename="reporting-obligation",
)

urlpatterns = router.urls
