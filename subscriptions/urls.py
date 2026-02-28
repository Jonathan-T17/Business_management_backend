from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet  # future admin-only

router = DefaultRouter()
urlpatterns = router.urls