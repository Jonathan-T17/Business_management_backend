from rest_framework.routers import DefaultRouter

from .views import (
    ProjectViewSet,
    ProjectMembershipViewSet,
)


router = DefaultRouter()

router.register(
    r"projects",
    ProjectViewSet,
    basename="projects",
)

router.register(
    r"project-members",
    ProjectMembershipViewSet,
    basename="project-members",
)


urlpatterns = router.urls