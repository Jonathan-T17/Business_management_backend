from rest_framework.routers import DefaultRouter

from .views import (
    TaskViewSet,
    TaskActivityViewSet,
)


router = DefaultRouter()

router.register(
    "tasks",
    TaskViewSet,
    basename="tasks",
)

router.register(
    "task-activities",
    TaskActivityViewSet,
    basename="task-activities",
)


urlpatterns = router.urls