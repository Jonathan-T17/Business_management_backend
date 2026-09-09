from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PlanViewSet,
    SubscriptionViewSet,
    SubscriptionFeaturesView,
    SubscriptionUsageView,
)


router = DefaultRouter()

router.register(
    "plans",
    PlanViewSet,
    basename="plans",
)

router.register(
    "platform/plans",
    PlanViewSet,
    basename="platform-plans",
)

router.register(
    "subscriptions",
    SubscriptionViewSet,
    basename="subscriptions",
)

urlpatterns = [
    path("subscriptions/usage/", SubscriptionUsageView.as_view(), name="subscription-usage"),
    path("subscriptions/features/", SubscriptionFeaturesView.as_view(), name="subscription-features"),
]

urlpatterns += router.urls
