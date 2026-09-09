from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    TeamViewSet,
    PositionViewSet,
    EmployeeProfileViewSet,
    EmployeeDelegationViewSet,
    EmployeeCompensationViewSet,
    UserCapabilityGrantViewSet,
    PositionCapabilityGrantViewSet,
    EmployeeTransferViewSet,
    EmployeeNoteViewSet,
    CapabilityCatalogueView,
    RolePresetView,
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
    r"employee-delegations",
    EmployeeDelegationViewSet,
    basename="organization-employee-delegation",
)

router.register(
    r"employee-compensations",
    EmployeeCompensationViewSet,
    basename="employee-compensation",
)

router.register(
    r"capability-grants",
    UserCapabilityGrantViewSet,
    basename="capability-grant",
)

router.register(
    r"position-capability-grants",
    PositionCapabilityGrantViewSet,
    basename="position-capability-grant",
)

router.register(
    r"employee-notes",
    EmployeeNoteViewSet,
    basename="organization-employee-note",
)


urlpatterns = [
    path(
        "capabilities/catalog/",
        CapabilityCatalogueView.as_view(),
        name="capability-catalogue",
    ),
    path(
        "role-presets/apply/",
        RolePresetView.as_view(),
        name="role-preset-apply",
    ),
]

urlpatterns += router.urls