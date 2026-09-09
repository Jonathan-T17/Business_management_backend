from rest_framework.routers import DefaultRouter

from .views import (
    WorkflowDefinitionViewSet,
    WorkflowInstanceViewSet,
)


router = DefaultRouter()

router.register(
    "workflow-definitions",
    WorkflowDefinitionViewSet,
    basename="workflow-definition",
)

router.register(
    "workflow-instances",
    WorkflowInstanceViewSet,
    basename="workflow-instance",
)

urlpatterns = router.urls