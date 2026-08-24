from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PlanViewSet,
    SubscriptionViewSet,
)


router = DefaultRouter()

router.register(
    "plans",
    PlanViewSet,
    basename="plans",
)

router.register(
    "subscriptions",
    SubscriptionViewSet,
    basename="subscriptions",
)

urlpatterns = router.urls
