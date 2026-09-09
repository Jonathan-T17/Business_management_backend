from rest_framework.routers import DefaultRouter

from .views import (
    CompanyPlanViewSet,
    PlanItemViewSet,
)


router = DefaultRouter()

router.register(
    "company-plans",
    CompanyPlanViewSet,
    basename="company-plan",
)

router.register(
    "plan-items",
    PlanItemViewSet,
    basename="plan-item",
)

urlpatterns = router.urls