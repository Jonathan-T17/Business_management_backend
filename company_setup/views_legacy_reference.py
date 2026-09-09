from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from security.services import create_audit_log
from core.capabilities import Capabilities
from organizations.models import EmployeeProfile, Position, PositionCapabilityGrant, UserCapabilityGrant
from organizations.services import CapabilityGrantService
from documents.models import DocumentCategory
from documents.serializers import DocumentCategorySerializer

from .models import ApprovalRoute, BusinessSetupTemplate, CompanySetupState, FieldActivityTemplate, NotificationPolicy, OfficialRecordPolicy, ReportingProcess, RequestTypeDefinition, RolePreset
from .permissions import IsCompanySetupAdmin
from .selectors import SetupHealthService
from .serializers import (
    BusinessSetupTemplateSerializer,
    CompanySetupStateSerializer,
    RolePresetSerializer,
    RequestTypeDefinitionSerializer,
    FieldActivityTemplateSerializer,
    ApprovalRouteSerializer,
    ReportingProcessSerializer,
    NotificationPolicySerializer,
    OfficialRecordPolicySerializer,
)
from .services import ApprovalRouteService, BusinessSetupTemplateService, ReportingProcessService


SETUP_STEPS = (("company", "Company Profile"), ("organization", "Organization"), ("employees", "Employees"), ("permissions", "Roles and Permissions"), ("reporting", "Reporting"), ("workflows", "Approvals"))


class SetupBaseView(APIView):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_state(self, company):
        state, _ = CompanySetupState.objects.get_or_create(company=company)
        return state


class SetupStatusView(SetupBaseView):
    def get(self, request):
        state = self.get_state(request.user.company)
        completed, skipped = set(state.completed_steps), set(state.skipped_steps)
        steps = [{"code": code, "name": name, "status": "COMPLETED" if code in completed else "SKIPPED" if code in skipped else "IN_PROGRESS" if code == state.current_step else "NOT_STARTED"} for code, name in SETUP_STEPS]
        progress = round((len(completed | skipped) / len(SETUP_STEPS)) * 100)
        return Response({"completed": state.onboarding_completed, "progress": progress, "current_step": state.current_step, "steps": steps})


class SetupOnboardingView(SetupBaseView):
    def get(self, request):
        return Response(
            CompanySetupStateSerializer(
                self.get_state(request.user.company),
            ).data
        )

    def patch(self, request):
        state = self.get_state(request.user.company)
        serializer = CompanySetupStateSerializer(
            state,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        valid_steps = {code for code, _ in SETUP_STEPS}
        completed_steps = set(serializer.validated_data.get("completed_steps", state.completed_steps))
        skipped_steps = set(serializer.validated_data.get("skipped_steps", state.skipped_steps))
        current_step = serializer.validated_data.get("current_step", state.current_step)

        invalid_steps = (completed_steps | skipped_steps | ({current_step} if current_step else set())) - valid_steps
        if invalid_steps:
            raise ValidationError({"steps": f"Invalid setup steps: {', '.join(sorted(invalid_steps))}."})

        state.completed_steps = sorted(completed_steps)
        state.skipped_steps = sorted(skipped_steps - completed_steps)
        state.current_step = current_step
        state.selected_template = serializer.validated_data.get("selected_template", state.selected_template)
        state.onboarding_completed = len(set(state.completed_steps) | set(state.skipped_steps)) == len(SETUP_STEPS)
        state.save()
        create_audit_log(user=request.user, company=request.user.company, request=request, action="UPDATE", description="Company onboarding state updated.", obj=state)
        return Response(CompanySetupStateSerializer(state).data)


class SetupStepCompleteView(SetupBaseView):
    def post(self, request):
        step = request.data.get("step")
        if step not in {code for code, _ in SETUP_STEPS}:
            raise ValidationError({"step": "Invalid setup step."})
        state = self.get_state(request.user.company)
        state.completed_steps = sorted(set(state.completed_steps) | {step})
        state.skipped_steps = sorted(set(state.skipped_steps) - {step})
        state.current_step = ""
        state.onboarding_completed = len(set(state.completed_steps) | set(state.skipped_steps)) == len(SETUP_STEPS)
        state.save()
        create_audit_log(user=request.user, company=request.user.company, request=request, action="UPDATE", description=f"Completed company setup step: {step}.", obj=state)
        return Response(CompanySetupStateSerializer(state).data)


class SetupHealthView(SetupBaseView):
    def get(self, request):
        return Response(SetupHealthService.evaluate(request.user.company))


class CompanySetupCapabilitiesView(SetupBaseView):
    def get(self, request):
        return Response([
            capability
            for capability in Capabilities.catalogue()
            if capability["tenant_assignable"]
        ])


class CapabilityAssignmentView(SetupBaseView):
    grant_model = None
    object_model = None
    object_field = ""

    def get_target(self, pk):
        return self.object_model.objects.get(
            pk=pk,
            company=self.request.user.company,
        )

    def get(self, request, pk):
        try:
            target = self.get_target(pk)
        except self.object_model.DoesNotExist:
            raise ValidationError({"id": "Unknown company resource."})
        filters = {"company": request.user.company, self.object_field: target, "is_active": True}
        grants = self.grant_model.objects.filter(**filters).values_list("capability", flat=True)
        return Response({"capabilities": sorted(grants)})


class PositionCapabilitiesView(CapabilityAssignmentView):
    grant_model = PositionCapabilityGrant
    object_model = Position
    object_field = "position"

    def put(self, request, pk):
        capabilities = set(request.data.get("capabilities", []))
        if not capabilities.issubset(set(Capabilities.values()) - Capabilities.PLATFORM_ONLY):
            raise ValidationError({"capabilities": "Invalid or platform-only capability."})
        try:
            position = self.get_target(pk)
        except Position.DoesNotExist:
            raise ValidationError({"id": "Unknown position."})
        active_grants = PositionCapabilityGrant.objects.filter(company=request.user.company, position=position, is_active=True)
        active_grants.exclude(capability__in=capabilities).update(is_active=False)
        for capability in capabilities:
            CapabilityGrantService.grant_position(company=request.user.company, position=position, capability=capability, actor=request.user, request=request)
        return self.get(request, pk)


class EmployeeProfileCapabilitiesView(CapabilityAssignmentView):
    grant_model = UserCapabilityGrant
    object_model = EmployeeProfile
    object_field = "user"

    def get_target(self, pk):
        return self.object_model.objects.select_related("user").get(pk=pk, company=self.request.user.company)

    def put(self, request, pk):
        capabilities = set(request.data.get("capabilities", []))
        if not capabilities.issubset(set(Capabilities.values()) - Capabilities.PLATFORM_ONLY):
            raise ValidationError({"capabilities": "Invalid or platform-only capability."})
        try:
            profile = self.get_target(pk)
        except EmployeeProfile.DoesNotExist:
            raise ValidationError({"id": "Unknown employee profile."})
        active_grants = UserCapabilityGrant.objects.filter(company=request.user.company, user=profile.user, is_active=True)
        active_grants.exclude(capability__in=capabilities).update(is_active=False)
        for capability in capabilities:
            CapabilityGrantService.grant_user(company=request.user.company, target_user=profile.user, capability=capability, actor=request.user, request=request)
        return self.get(request, pk)


class BusinessSetupTemplateListView(SetupBaseView):
    def get(self, request):
        templates = BusinessSetupTemplate.objects.filter(is_active=True)
        return Response(BusinessSetupTemplateSerializer(templates, many=True).data)


class BusinessSetupTemplateDetailView(SetupBaseView):
    def get_template(self, code):
        try:
            return BusinessSetupTemplate.objects.get(code=code, is_active=True)
        except BusinessSetupTemplate.DoesNotExist:
            raise ValidationError({"code": "Unknown active setup template."})

    def get(self, request, code):
        return Response(BusinessSetupTemplateSerializer(self.get_template(code)).data)


class BusinessSetupTemplateApplyView(BusinessSetupTemplateDetailView):
    def post(self, request, code):
        template = self.get_template(code)
        created = BusinessSetupTemplateService.apply(company=request.user.company, template=template, selections=request.data, actor=request.user, request=request)
        state = self.get_state(request.user.company)
        state.selected_template = template.code
        state.save(update_fields=["selected_template", "updated_at"])
        return Response({"template": template.code, "created": created}, status=status.HTTP_200_OK)


class RolePresetViewSet(viewsets.ModelViewSet):
    serializer_class = RolePresetSerializer
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = RolePreset.objects.filter(is_active=True)
        if user.role == "SUPERUSER":
            return queryset
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        preset = serializer.save(company=self.request.user.company)
        create_audit_log(user=self.request.user, company=self.request.user.company, request=self.request, action="CREATE", description=f"Created role preset: {preset.name}.", obj=preset)

    def perform_update(self, serializer):
        preset = serializer.save()
        create_audit_log(user=self.request.user, company=preset.company, request=self.request, action="UPDATE", description=f"Updated role preset: {preset.name}.", obj=preset)


class CompanyConfigurationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        create_audit_log(user=self.request.user, company=instance.company, request=self.request, action="CREATE", description=f"Created {instance._meta.verbose_name}: {instance}.", obj=instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        create_audit_log(user=self.request.user, company=instance.company, request=self.request, action="UPDATE", description=f"Updated {instance._meta.verbose_name}: {instance}.", obj=instance)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=["is_active"])
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        return Response(self.get_serializer(instance).data)


class CompanySetupDocumentCategoryViewSet(CompanyConfigurationViewSet):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer


class RequestTypeDefinitionViewSet(CompanyConfigurationViewSet):
    queryset = RequestTypeDefinition.objects.select_related("workflow", "form_template")
    serializer_class = RequestTypeDefinitionSerializer


class FieldActivityTemplateViewSet(CompanyConfigurationViewSet):
    queryset = FieldActivityTemplate.objects.select_related("form_template")
    serializer_class = FieldActivityTemplateSerializer


class ApprovalRouteViewSet(viewsets.ModelViewSet):
    serializer_class = ApprovalRouteSerializer
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_queryset(self):
        return ApprovalRoute.objects.filter(company=self.request.user.company).select_related("workflow").prefetch_related("workflow__steps")

    def create(self, request):
        try:
            route = ApprovalRouteService.create(company=request.user.company, data=request.data.copy(), actor=request.user, request=request)
        except ValueError as error:
            raise ValidationError({"steps": str(error)})
        return Response(self.get_serializer(route).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        route = self.get_object()
        try:
            route = ApprovalRouteService.update(route=route, data=request.data.copy(), actor=request.user, request=request)
        except ValueError as error:
            raise ValidationError({"steps": str(error)})
        return Response(self.get_serializer(route).data)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        try:
            ApprovalRouteService.validate_steps(company=request.user.company, steps=request.data.get("steps", []))
        except ValueError as error:
            return Response({"resolved_route": [], "warnings": [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"resolved_route": [{"step": index, "recipient_type": step["recipient_type"]} for index, step in enumerate(request.data["steps"], start=1)], "warnings": []})


class ReportingProcessViewSet(viewsets.ModelViewSet):
    serializer_class = ReportingProcessSerializer
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    def get_queryset(self):
        return ReportingProcess.objects.filter(company=self.request.user.company).select_related("schedule", "schedule__template", "approval_route")

    def create(self, request):
        try:
            process = ReportingProcessService.create(company=request.user.company, data=request.data, actor=request.user, request=request)
        except ValueError as error:
            raise ValidationError({"detail": str(error)})
        return Response(self.get_serializer(process).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        process = self.get_object()
        try:
            process = ReportingProcessService.update(process=process, data=request.data.copy(), actor=request.user, request=request)
        except ValueError as error:
            raise ValidationError({"detail": str(error)})
        return Response(self.get_serializer(process).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        process = self.get_object()
        process.is_active = True
        process.schedule.is_active = True
        process.schedule.save(update_fields=["is_active"])
        process.save(update_fields=["is_active"])
        return Response(self.get_serializer(process).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        process = self.get_object()
        process.is_active = False
        process.schedule.is_active = False
        process.schedule.save(update_fields=["is_active"])
        process.save(update_fields=["is_active"])
        return Response(self.get_serializer(process).data)


class OfficialRecordPolicyViewSet(CompanyConfigurationViewSet):
    queryset = OfficialRecordPolicy.objects.all()
    serializer_class = OfficialRecordPolicySerializer


class NotificationPolicyViewSet(CompanyConfigurationViewSet):
    queryset = NotificationPolicy.objects.all()
    serializer_class = NotificationPolicySerializer