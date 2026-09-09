from rest_framework.routers import DefaultRouter

from .views import BusinessRequestViewSet


router = DefaultRouter()

router.register(
    "business-requests",
    BusinessRequestViewSet,
    basename="business-request",
)

urlpatterns = router.urls