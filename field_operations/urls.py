from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    FieldActivityViewSet,
    FieldStopViewSet,
)


router = DefaultRouter()

router.register(
    "field-activities",
    FieldActivityViewSet,
    basename="field-activity",
)

router.register(
    "field-stops",
    FieldStopViewSet,
    basename="field-stop",
)

urlpatterns = router.urls