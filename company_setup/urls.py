from django.urls import path
from .views import (
    SetupAccessView,
    SetupTemplatesView, SetupTemplateApplyView,
    SetupFinishView, SetupHealthView, SetupStatusView,
    SetupStepCompleteView, SetupStepSkipView,
)

urlpatterns = [
    path("access/", SetupAccessView.as_view(), name="company-setup-access"),
    path("templates/", SetupTemplatesView.as_view()),
    path("templates/<slug:code>/apply/", SetupTemplateApplyView.as_view()),
    path("status/", SetupStatusView.as_view(), name="company-setup-status"),
    path("health/", SetupHealthView.as_view(), name="company-setup-health"),
    path("steps/complete/", SetupStepCompleteView.as_view(), name="company-setup-step-complete"),
    path("steps/skip/", SetupStepSkipView.as_view(), name="company-setup-step-skip"),
    path("finish/", SetupFinishView.as_view(), name="company-setup-finish"),
]


from rest_framework.routers import DefaultRouter
from .configuration_views import (RolePresetViewSet, RequestTypeViewSet, FieldTemplateViewSet,
                                 DocumentCategoryViewSet, RecordPolicyViewSet, NotificationPolicyViewSet)
router = DefaultRouter()
from .reporting_views import ReportingProcessViewSet
router.register("reporting-processes", ReportingProcessViewSet, basename="setup-reporting-processes")
from .approval_views import ApprovalRouteViewSet
router.register("approval-routes", ApprovalRouteViewSet, basename="setup-approval-routes")
router.register('role-presets', RolePresetViewSet, basename='setup-role-presets')
router.register('request-types', RequestTypeViewSet, basename='setup-request-types')
router.register('field-templates', FieldTemplateViewSet, basename='setup-field-templates')
router.register('document-categories', DocumentCategoryViewSet, basename='setup-document-categories')
router.register('official-record-policies', RecordPolicyViewSet, basename='setup-record-policies')
router.register('notification-policies', NotificationPolicyViewSet, basename='setup-notification-policies')
urlpatterns += router.urls
from .configuration_views import SetupCapabilitiesView
urlpatterns += [path('capabilities/', SetupCapabilitiesView.as_view(), name='setup-capabilities')]

from .position_access import PositionAccessView
urlpatterns += [path("positions/<int:pk>/access/", PositionAccessView.as_view(), name="setup-position-access")]
