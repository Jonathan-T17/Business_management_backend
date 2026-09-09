from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ApprovalRouteViewSet, BusinessSetupTemplateApplyView, BusinessSetupTemplateDetailView, BusinessSetupTemplateListView, CompanySetupCapabilitiesView, CompanySetupDocumentCategoryViewSet, EmployeeProfileCapabilitiesView, FieldActivityTemplateViewSet, NotificationPolicyViewSet, OfficialRecordPolicyViewSet, PositionCapabilitiesView, ReportingProcessViewSet, RequestTypeDefinitionViewSet, RolePresetViewSet, SetupHealthView, SetupOnboardingView, SetupStatusView, SetupStepCompleteView

router = DefaultRouter()
router.register("role-presets", RolePresetViewSet, basename="company-setup-role-preset")
router.register("request-types", RequestTypeDefinitionViewSet, basename="company-setup-request-type")
router.register("field-templates", FieldActivityTemplateViewSet, basename="company-setup-field-template")
router.register("approval-routes", ApprovalRouteViewSet, basename="company-setup-approval-route")
router.register("reporting-processes", ReportingProcessViewSet, basename="company-setup-reporting-process")
router.register("official-record-policies", OfficialRecordPolicyViewSet, basename="company-setup-official-record-policy")
router.register("notification-policies", NotificationPolicyViewSet, basename="company-setup-notification-policy")
router.register("document-categories", CompanySetupDocumentCategoryViewSet, basename="company-setup-document-category")

urlpatterns = [
    path("status/", SetupStatusView.as_view(), name="company-setup-status"),
    path("health/", SetupHealthView.as_view(), name="company-setup-health-v2"),
    path("capabilities/", CompanySetupCapabilitiesView.as_view(), name="company-setup-capabilities"),
    path("positions/<int:pk>/capabilities/", PositionCapabilitiesView.as_view(), name="company-setup-position-capabilities"),
    path("employee-profiles/<int:pk>/capabilities/", EmployeeProfileCapabilitiesView.as_view(), name="company-setup-employee-profile-capabilities"),
    path("onboarding/", SetupOnboardingView.as_view(), name="company-setup-onboarding"),
    path("steps/complete/", SetupStepCompleteView.as_view(), name="company-setup-step-complete"),
    path("templates/", BusinessSetupTemplateListView.as_view(), name="business-setup-template-list"),
    path("templates/<slug:code>/", BusinessSetupTemplateDetailView.as_view(), name="business-setup-template-detail"),
    path("templates/<slug:code>/apply/", BusinessSetupTemplateApplyView.as_view(), name="business-setup-template-apply"),
]

urlpatterns += router.urls