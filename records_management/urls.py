from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OfficialRecordViewSet, verify_record

router = DefaultRouter()
router.register("official-records", OfficialRecordViewSet, basename="official-records")

urlpatterns = router.urls + [
    path(
        "official-records/verify/<uuid:token>/",
        verify_record,
        name="verify-official-record",
    ),
]
