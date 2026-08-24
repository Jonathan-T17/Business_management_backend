from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    TeamViewSet,
    PositionViewSet,
    EmployeeProfileViewSet,
    EmployeeTransferViewSet,
    EmployeeNoteViewSet,
)


router = DefaultRouter()

router.register(
    r"departments",
    DepartmentViewSet,
    basename="organization-department",
)

router.register(
    r"teams",
    TeamViewSet,
    basename="organization-team",
)

router.register(
    r"positions",
    PositionViewSet,
    basename="organization-position",
)

router.register(
    r"employees",
    EmployeeProfileViewSet,
    basename="organization-employee",
)

router.register(
    r"employee-transfers",
    EmployeeTransferViewSet,
    basename="organization-employee-transfer",
)

router.register(
    r"employee-notes",
    EmployeeNoteViewSet,
    basename="organization-employee-note",
)


urlpatterns = router.urls