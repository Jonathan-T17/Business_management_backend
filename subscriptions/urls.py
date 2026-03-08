from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet  # future admin-only

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscriptions")
urlpatterns = router.urls