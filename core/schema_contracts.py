"""Schema-only descriptions for APIViews that assemble their own payloads.

Extensions replace views only during documentation generation. They neither bypass
permissions nor change runtime validation. Keep these contracts aligned with tests.
"""
from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer, OpenApiParameter
from rest_framework import serializers as s


def contract(target, *, model_label=None, **methods):
    def replacement(self):
        attributes = {}
        serializer = getattr(self.target, "serializer_class", None)
        model = getattr(getattr(serializer, "Meta", None), "model", None)
        if model_label:
            from django.apps import apps
            model = apps.get_model(model_label)
        if model is not None:
            # Schema inspection needs model metadata, never tenant data or a real user.
            attributes["get_queryset"] = lambda view: model.objects.none()
        view = type(self.target.__name__ + "Schema", (self.target,), attributes)
        return extend_schema_view(**methods)(view)
    type(target.replace(".", "_") + "Contract", (OpenApiViewExtension,), {
        "target_class": target, "view_replacement": replacement,
    })


def shape(component_name, **fields):
    return inline_serializer(name=component_name, fields=fields)


def strings():
    return s.ListField(child=s.CharField())


Message = shape("MessageResponse", message=s.CharField())
Email = shape("EmailRequest", email=s.EmailField())
Verification = shape("VerificationRequest", uid=s.CharField(), token=s.CharField())
Reset = shape("PasswordResetRequest", uid=s.CharField(), token=s.CharField(), password=s.CharField(write_only=True))
Reason = shape("OptionalReasonRequest", reason=s.CharField(required=False, allow_blank=True))
LoginUser = shape("LoginUser", id=s.UUIDField(), email=s.EmailField(), full_name=s.CharField(), role=s.CharField())
LoginTokens = shape("LoginTokens", access=s.CharField(), refresh=s.CharField(), user=LoginUser)
OTPChallenge = shape("OTPChallenge", otp_required=s.BooleanField(), message=s.CharField(), email=s.EmailField(),
    challenge_id=s.UUIDField(), verify_url=s.CharField(), expires_in=s.IntegerField())
OTPRequest = shape("OTPRequest", challenge_id=s.UUIDField(), code=s.CharField(),
    email=s.EmailField(required=False), trust_device=s.BooleanField(required=False))
OTPResult = shape("OTPResult", access=s.CharField(), refresh=s.CharField(), user=LoginUser,
    otp_required=s.BooleanField(), device_token=s.CharField(allow_null=True), trusted_device_token=s.CharField(allow_null=True))

# Error shapes intentionally preserve both explicit view responses and exception-handler envelopes.
Error = {"oneOf": [
    {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]},
    {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
    {"type": "object", "properties": {"error": {"type": "array", "items": {"type": "string"}}}, "required": ["error"]},
    {"type": "object", "properties": {"error": {"type": "object", "properties": {
        "code": {"type": "string"}, "message": {"type": "string"}, "request_id": {"type": "string"}, "fields": {},
    }, "required": ["code", "message", "request_id"]}}, "required": ["error"]},
]}

from users.serializers import UserRegisterSerializer, ThemePreferenceSerializer

contract("users.views.RegisterView", post=extend_schema(request=UserRegisterSerializer, responses={201: Message, 400: {"type": "object", "additionalProperties": {}}, 500: Error}))
contract("users.views.VerifyEmailView", post=extend_schema(request=Verification, responses={200: Message, 400: Error}))
for target in ("ResendVerificationView", "RequestPasswordResetView"):
    contract("users.views." + target, post=extend_schema(request=Email, responses={200: Message}))
contract("users.views.ConfirmPasswordResetView", post=extend_schema(request=Reset, responses={200: Message, 400: Error}))
contract("users.views.LogoutView", post=extend_schema(request=shape("LogoutRequest", refresh=s.CharField()), responses={205: Message, 400: Error}))
contract("users.views.VerifyOTPView", post=extend_schema(request=OTPRequest, responses={200: OTPResult, 400: Error}))
for target in ("ActivateUserView", "DeactivateUserView"):
    contract("users.views." + target, post=extend_schema(request=Reason, responses={200: Message, 400: Error, 404: Error}))
contract("users.views.ChangeUserRoleView", post=extend_schema(
    request=shape("RoleChangeRequest", role=s.CharField(), reason=s.CharField(required=False)),
    responses={200: shape("RoleChangeResponse", message=s.CharField(), role=s.CharField()), 400: Error, 404: Error}))
contract("users.auth_views.CustomLoginView", post=extend_schema(
    request=shape("LoginRequest", email=s.EmailField(), password=s.CharField(write_only=True), device_token=s.CharField(required=False)),
    parameters=[OpenApiParameter("X-SmartBiz-Device-Token", str, OpenApiParameter.HEADER)],
    responses={200: LoginTokens, 202: OTPChallenge, 400: Error, 401: Error, 429: Error, 503: Error}))
contract("users.views.UserViewSet", preferences=extend_schema(request=ThemePreferenceSerializer, responses=ThemePreferenceSerializer))

from companies.serializers import PublicInviteSerializer
contract("companies.views.InvitationInfoView", get=extend_schema(responses=PublicInviteSerializer))
contract("companies.views.AcceptInvitationView", post=extend_schema(request=None,
    responses=shape("InvitationAccepted", message=s.CharField(), company_id=s.IntegerField(), role=s.CharField())))

from data_tools.serializers import SearchResultSerializer, ImportJobStatusSerializer
contract("data_tools.views.GlobalSearchView", get=extend_schema(
    parameters=[OpenApiParameter("q", str, required=True), OpenApiParameter("limit", int)], responses=SearchResultSerializer(many=True)))
contract("data_tools.views.BulkTaskStatusView", post=extend_schema(
    request=shape("BulkTaskStatusRequest", ids=s.ListField(child=s.IntegerField()), status=s.CharField()),
    responses=shape("BulkTaskStatusResponse", updated=s.IntegerField())))
contract("data_tools.views.EmployeeImportView", post=extend_schema(
    request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}, "required": ["file"]}},
    responses=ImportJobStatusSerializer))
contract("data_tools.views.EmployeeImportCommitView", post=extend_schema(request=None, responses=ImportJobStatusSerializer))
contract("data_tools.views.EmployeeImportStatusView", get=extend_schema(responses=ImportJobStatusSerializer))
contract("data_tools.views.RequestCSVExportView", get=extend_schema(
    parameters=[OpenApiParameter("purpose", str, required=True)], responses={(200, "text/csv"): {"type": "string"}}))

UsageCount = shape("UsageCount", used=s.IntegerField(), limit=s.IntegerField())
contract("subscriptions.views.SubscriptionUsageView", get=extend_schema(responses=shape("SubscriptionUsage",
    users=UsageCount, projects=UsageCount, branches=UsageCount,
    storage=shape("StorageUsage", used_bytes=s.IntegerField(), limit_bytes=s.IntegerField()))))
contract("subscriptions.views.SubscriptionFeaturesView", get=extend_schema(responses=shape("SubscriptionFeatures",
    features=s.DictField(child=s.BooleanField()))))

Capability = shape("CapabilityDefinition", code=s.CharField(), name=s.CharField(), description=s.CharField(),
    category=s.CharField(), sensitive=s.BooleanField(), assignable_by_company_admin=s.BooleanField(), tenant_assignable=s.BooleanField())
contract("company_setup.configuration_views.SetupCapabilitiesView", get=extend_schema(responses=type(Capability)(many=True)))
Preset = shape("CapabilityPreset", code=s.CharField(), name=s.CharField(), capabilities=strings())
contract("organizations.views.CapabilityCatalogueView", get=extend_schema(responses=shape("CapabilityCatalogue",
    capabilities=type(Capability)(many=True), presets=type(Preset)(many=True))))
from organizations.serializers import PositionCapabilityGrantSerializer
contract("organizations.views.RolePresetView", post=extend_schema(
    request=shape("ApplyRolePresetRequest", position=s.IntegerField(), preset=s.CharField()),
    responses=shape("AppliedRolePreset", preset=s.CharField(), position=s.CharField(), grants=PositionCapabilityGrantSerializer(many=True))))

ReadinessCheck = shape("ReadinessCheck", code=s.CharField(), severity=s.CharField(), passed=s.BooleanField(),
    message=s.CharField(), destination=s.CharField(), blocking=s.BooleanField())
ReadinessIssue = shape("ReadinessIssue", code=s.CharField(), severity=s.CharField(), message=s.CharField(), url=s.CharField())
Readiness = shape("SetupReadiness", ready=s.BooleanField(), score=s.IntegerField(), status=s.CharField(),
    blocking_count=s.IntegerField(), warning_count=s.IntegerField(), checks=type(ReadinessCheck)(many=True),
    issues=type(ReadinessIssue)(many=True))
Step = shape("SetupStep", code=s.CharField(), name=s.CharField(), required=s.BooleanField(), status=s.CharField())
contract("company_setup.views.SetupStatusView", get=extend_schema(responses=shape("SetupStatus",
    completed=s.BooleanField(), progress=s.IntegerField(), onboarding_completed=s.BooleanField(), current_step=s.CharField(),
    selected_template=s.CharField(), steps=type(Step)(many=True), readiness=Readiness, allowed_actions=strings())))
contract("company_setup.views.SetupHealthView", get=extend_schema(responses=shape("SetupHealth",
    **type(Readiness)().fields, completed_steps=strings())))
contract("company_setup.views.SetupStepCompleteView", post=extend_schema(
    request=shape("CompleteSetupStep", step=s.CharField()),
    responses=shape("CompletedSetupStep", current_step=s.CharField(), completed_steps=strings())))
contract("company_setup.views.SetupStepSkipView", post=extend_schema(
    request=shape("SkipSetupStep", step=s.CharField(), reason=s.CharField()),
    responses=shape("SkippedSetupStep", skipped_steps=strings())))
contract("company_setup.views.SetupFinishView", post=extend_schema(request=None,
    responses=shape("SetupFinished", onboarding_completed=s.BooleanField())))
from company_setup.serializers import BusinessSetupTemplateSerializer
contract("company_setup.views.SetupTemplatesView", get=extend_schema(responses=BusinessSetupTemplateSerializer(many=True)))
contract("company_setup.views.SetupTemplateApplyView", post=extend_schema(
    request=shape("TemplateSelection", departments=s.BooleanField(default=True), positions=s.BooleanField(default=True), document_categories=s.BooleanField(default=True)),
    responses=shape("TemplateApplied", template=s.CharField(), created=shape("TemplateCreatedCounts",
        departments=s.IntegerField(), positions=s.IntegerField(), document_categories=s.IntegerField()))))

from analytics_ai.serializers import AnalyticsSnapshotSerializer, AIInsightSerializer, SnapshotWithInsightSerializer
CompanyAnalytics = shape("CompanyAnalytics", company_id=s.IntegerField(), snapshots=AnalyticsSnapshotSerializer(many=True), insights=AIInsightSerializer(many=True))
contract("analytics_ai.views.CompanyAnalyticsView", get=extend_schema(
    parameters=[OpenApiParameter("project_id", int), OpenApiParameter("branch_id", int)], responses=CompanyAnalytics))
contract("analytics_ai.views.GenerateCompanyAnalyticsView", post=extend_schema(request=None, responses={201: shape("GeneratedCompanyAnalytics",
    snapshot=AnalyticsSnapshotSerializer(), insights=AIInsightSerializer(many=True))}))
for target in ("GenerateProjectAnalyticsView", "GenerateBranchAnalyticsView"):
    contract("analytics_ai.views." + target, post=extend_schema(request=None, responses={201: SnapshotWithInsightSerializer}))
from analytics_ai.overview import OverviewFilters
Metric = shape("OverviewMetric", key=s.CharField(), label=s.CharField(), value=s.IntegerField())
contract("analytics_ai.overview.AnalyticsOverviewView", get=extend_schema(parameters=[OverviewFilters],
    responses=shape("AnalyticsOverview", metrics=type(Metric)(many=True),
        submissions=s.DictField(child=s.IntegerField()),
        submission_trend=type(shape("SubmissionTrendPoint", date=s.DateField(), value=s.IntegerField()))(many=True),
        tasks=shape("OverviewTaskCounts", **{key: s.IntegerField() for key in ("total", "todo", "in_progress", "done", "overdue")}),
        requests=shape("OverviewRequestCounts", **{key: s.IntegerField() for key in ("submitted", "under_review", "approved", "rejected", "fulfilled")}))))

HealthStatus = shape("HealthStatus", status=s.CharField())
Health = shape("PlatformHealth", status=s.CharField(), database=HealthStatus, cache=HealthStatus,
    email=shape("EmailHealth", status=s.CharField(), backend=s.CharField()), timestamp=s.DateTimeField())
contract("platform_admin.views.PlatformHealthView", get=extend_schema(responses=Health))
contract("platform_admin.views.PlatformSettingsView", get=extend_schema(responses=shape("PlatformSettings",
    editable=s.BooleanField(), message=s.CharField(), settings=shape("DeploymentSettings",
        access_token_minutes=s.IntegerField(), refresh_token_days=s.IntegerField(), frontend_url=s.CharField(), email_configured=s.BooleanField()))))
from platform_admin.serializers import PlatformCompanySerializer, PlatformAuditLogSerializer
contract("platform_admin.views.PlatformDashboardView", get=extend_schema(responses=shape("PlatformDashboard",
    **{name: shape("Platform" + name.title() + "Counts", **{key: s.IntegerField() for key in keys}) for name, keys in {
        "companies": ("total", "active", "new_this_month"), "users": ("total", "active", "new_this_month"),
        "projects": ("total", "active"), "tasks": ("total", "active", "completed"), "reports": ("total", "last_24h"),
        "communications": ("sent_24h", "failed_24h", "pending"), "trend": ("last_7_days_sent", "last_7_days_failed"),
        "security": ("active_sessions", "failed_logins_24h", "locked_records", "critical_events_24h"),
        "subscriptions": ("active", "expired", "expiring_soon"),
    }.items()}, success_rate=s.FloatField(), failure_rate=s.FloatField(), system_health=Health,
    recent_audit_events=PlatformAuditLogSerializer(many=True), recent_companies=PlatformCompanySerializer(many=True))))

DashboardTask = shape("DashboardTask", id=s.IntegerField(), title=s.CharField(), status=s.CharField(),
    project_id=s.IntegerField(allow_null=True), due_date=s.DateField(allow_null=True), is_overdue=s.BooleanField())
DashboardProject = shape("DashboardProject", id=s.IntegerField(), name=s.CharField(), description=s.CharField(), is_active=s.BooleanField())
DashboardActivity = shape("DashboardActivity", id=s.IntegerField(), action=s.CharField(), user_id=s.UUIDField(allow_null=True),
    project_id=s.IntegerField(allow_null=True), task_id=s.IntegerField(allow_null=True), metadata=s.JSONField(), created_at=s.DateTimeField())
contract("core.views.DashboardView", get=extend_schema(responses=shape("TenantDashboard",
    role=s.CharField(), dashboard=s.CharField(),
    user=shape("DashboardUser", id=s.UUIDField(), email=s.EmailField(), full_name=s.CharField(), role=s.CharField(), company_id=s.IntegerField(allow_null=True), branch_id=s.IntegerField(allow_null=True)),
    company=shape("DashboardCompany", id=s.IntegerField(), name=s.CharField(), slug=s.CharField()),
    summary=shape("DashboardSummary", **{key: s.IntegerField() for key in ("employees", "branches", "departments", "teams", "activity", "projects", "tasks", "reports", "unread_notifications")}, tasks_by_status=s.DictField(child=s.IntegerField())),
    recent_projects=type(DashboardProject)(many=True), recent_tasks=type(DashboardTask)(many=True), recent_activity=type(DashboardActivity)(many=True), endpoints=s.DictField(child=s.CharField()))))

# Maintenance records deliberately contain resource-specific JSON values, not arbitrary model serialization.
from platform_admin.maintenance import ChangeEnvelope
from drf_spectacular.utils import PolymorphicProxySerializer
MaintenanceRecord = shape("MaintenanceRecord", id=s.CharField(), label=s.CharField(), values=s.DictField(), version=s.CharField(), company=s.CharField())
MaintenanceChoice = shape("MaintenanceChoice", value=s.CharField(), label=s.CharField())
MaintenanceField = shape("MaintenanceField", name=s.CharField(), label=s.CharField(), kind=s.CharField(),
    required=s.BooleanField(), nullable=s.BooleanField(), choices=type(MaintenanceChoice)(many=True), default=s.JSONField(allow_null=True), max_length=s.IntegerField(allow_null=True))
MaintenanceList = shape("MaintenanceList", title=s.CharField(), description=s.CharField(), fields=type(MaintenanceField)(many=True),
    can_create=s.BooleanField(), count=s.IntegerField(), page=s.IntegerField(), results=type(MaintenanceRecord)(many=True))
CatalogueItem = shape("MaintenanceCatalogueItem", key=s.CharField(), title=s.CharField(), description=s.CharField(), can_create=s.BooleanField())
contract("platform_admin.maintenance.MaintenanceCatalogue", get=extend_schema(responses=type(CatalogueItem)(many=True)))
contract("platform_admin.maintenance.MaintenanceRecords",
    get=extend_schema(parameters=[OpenApiParameter("search", str), OpenApiParameter("page", int)], responses=PolymorphicProxySerializer(
        component_name="MaintenanceRead", serializers=[MaintenanceRecord, MaintenanceList], resource_type_field_name=None)),
    post=extend_schema(request=ChangeEnvelope, responses={200: MaintenanceRecord, 201: MaintenanceRecord}),
    put=extend_schema(request=ChangeEnvelope, responses=MaintenanceRecord))
MaintenanceRelationChoice = shape("MaintenanceRelationChoice", value=s.CharField(), label=s.CharField(), issues=s.ListField(child=s.CharField(), required=False))
contract("platform_admin.maintenance.MaintenanceChoices", get=extend_schema(
    parameters=[OpenApiParameter(name, str) for name in ("company", "search", "selected")], responses=type(MaintenanceRelationChoice)(many=True)))

for target in (
    "documents.views.AttachmentViewSet",
    "chat.views.ConversationViewSet", "chat.views.MessageViewSet",
    "security.views.CompanyActiveSessionViewSet", "security.views.CompanyAuditLogViewSet",
    "security.views.MySessionViewSet", "security.views.TrustedDeviceViewSet",
    "projects.views.ProjectMembershipViewSet", "projects.views.ProjectViewSet",
    "reporting_schedules.views.ReportingObligationViewSet", "reporting_schedules.views.ReportingScheduleViewSet",
    "subscriptions.views.SubscriptionViewSet", "tasks.views.TaskActivityViewSet",
):
    contract(target)
contract("support.views.SupportTicketViewSet", model_label="support.SupportTicket")

# Structured method fields need their real nested shapes rather than string fallbacks.
from drf_spectacular.utils import extend_schema_field
from support.serializers import SupportTicketDetailSerializer, SupportMessageSerializer
extend_schema_field(SupportMessageSerializer(many=True))(SupportTicketDetailSerializer.get_messages)

from company_setup.approval_views import RouteOutput
Recipient = shape("ApprovalRecipientOutput", type=s.CharField(), position_id=s.CharField(required=False),
    user_id=s.UUIDField(required=False), role=s.CharField(required=False))
ApprovalStep = shape("ApprovalStepOutput", order=s.IntegerField(), label=s.CharField(), recipient=Recipient,
    can_return=s.BooleanField(), can_reject=s.BooleanField(), approval_mode=s.CharField(), notify_email=s.BooleanField(), notify_in_app=s.BooleanField())
extend_schema_field(type(ApprovalStep)(many=True))(RouteOutput.get_steps)
from company_setup.reporting_views import ProcessOutput
extend_schema_field(shape("ReportingScheduleOutput", frequency=s.CharField(), due_time=s.CharField(),
    weekday=s.IntegerField(allow_null=True), day_of_month=s.IntegerField(allow_null=True)))(ProcessOutput.get_schedule)
extend_schema_field(shape("ReportingSubmittersOutput", type=s.CharField(), position_id=s.CharField()))(ProcessOutput.get_submitters)
ReportingField = shape("ReportingFieldOutput", key=s.CharField(), label=s.CharField(), type=s.CharField(), required=s.BooleanField())
extend_schema_field(type(ReportingField)(many=True))(ProcessOutput.get_form_fields)
extend_schema_field(type(ApprovalStep)(many=True))(ProcessOutput.get_approval_route)
from field_operations.serializers import FieldStopSerializer
FormOption = shape("FieldFormOption", id=s.IntegerField(), name=s.CharField())
extend_schema_field(type(FormOption)(many=True))(FieldStopSerializer.get_form_options)
from data_tools.serializers import ImportJobStatusSerializer
ImportFieldError = shape("ImportFieldError", field=s.CharField(), message=s.CharField())
ImportRowError = shape("ImportRowError", row=s.IntegerField(), errors=type(ImportFieldError)(many=True))
extend_schema_field(type(ImportRowError)(many=True))(ImportJobStatusSerializer.get_errors)
from workflows.serializers import WorkflowStepRecipientSerializer
DelegatedUser = shape("DelegatedUser", id=s.UUIDField(), name=s.CharField(), email=s.EmailField())
extend_schema_field(type(DelegatedUser)(allow_null=True))(WorkflowStepRecipientSerializer.get_delegated_from)
