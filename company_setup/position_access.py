from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from organizations.models import Position, PositionCapabilityGrant
from organizations.services import CapabilityGrantService
from security.services import create_audit_log
from .permissions import IsCompanySetupAdmin
from .capability_policy import SetupCapabilityPolicy

class PositionAccessInput(serializers.Serializer):
    capabilities = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    primary_scope = serializers.ChoiceField(choices=Position._meta.get_field("primary_scope").choices, required=False)


class PositionAccessResult(PositionAccessInput):
    scope_label = serializers.CharField(read_only=True)
    branch_capabilities = serializers.ListField(child=serializers.CharField(), read_only=True)


def access_summary(position):
    from core.position_scope import BRANCH_CAPABILITIES
    return {
        "capabilities": list(position.capability_grants.filter(company_id=position.company_id, is_active=True).values_list("capability", flat=True)),
        "primary_scope": position.primary_scope,
        "scope_label": position.branch.name if position.primary_scope == "BRANCH" and position.branch_id else "Company-wide",
        "branch_capabilities": sorted(BRANCH_CAPABILITIES),
    }


def validate_position_access(*, actor, position, values):
    capabilities = SetupCapabilityPolicy.validate_preset(actor=actor, capabilities=values["capabilities"])
    from core.position_scope import BRANCH_CAPABILITIES
    scope = values.get("primary_scope", position.primary_scope)
    if scope == "BRANCH":
        if not position.branch_id or not position.branch.is_active or position.branch.company_id != actor.company_id:
            raise serializers.ValidationError({"primary_scope": "Assign this position to an active company location first."})
        unsupported = set(capabilities) - BRANCH_CAPABILITIES
        if unsupported:
            raise serializers.ValidationError({"capabilities": "Remove permissions that do not support location-limited access: " + ", ".join(code.replace("_", " ").title() for code in sorted(unsupported))})
    if position.assignments.filter(is_active=True,scope="BRANCHES").exists() and set(capabilities)-BRANCH_CAPABILITIES:
        raise serializers.ValidationError("This position has branch-limited assignments. Use a separate position for company-wide permissions.")
    return capabilities, scope

class PositionAccessView(APIView):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    @extend_schema(responses=PositionAccessResult)
    def get(self, request, pk):
        position = get_object_or_404(Position, pk=pk, company=request.user.company)
        return Response(access_summary(position))

    @extend_schema(request=PositionAccessInput, responses=PositionAccessResult)
    @transaction.atomic
    def put(self, request, pk):
        position = get_object_or_404(Position.objects.select_for_update(), pk=pk, company=request.user.company, is_active=True)
        data = PositionAccessInput(data=request.data)
        data.is_valid(raise_exception=True)
        capabilities, scope = validate_position_access(actor=request.user, position=position, values=data.validated_data)
        position.primary_scope = scope
        position.save(update_fields=["primary_scope"])
        PositionCapabilityGrant.objects.filter(position=position,company=request.user.company,is_active=True).exclude(capability__in=capabilities).update(is_active=False)
        for capability in capabilities:
            CapabilityGrantService.grant_position(company=request.user.company,position=position,capability=capability,actor=request.user,reason="Company setup access review",request=request)
        create_audit_log(user=request.user,company=request.user.company,request=request,action="SECURITY",description=f"Position access reviewed: {position.title} ({scope}).",obj=position)
        return Response(access_summary(position))


class PositionImpactPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    from organizations.serializers import EmployeeAccessChangeSerializer
    results = EmployeeAccessChangeSerializer(many=True)


class PositionAccessPreviewView(APIView):
    from organizations.permissions import CanManageEmployees
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin, CanManageEmployees]

    @extend_schema(request=PositionAccessInput, responses=PositionImpactPageSerializer)
    def post(self, request, pk):
        from django.db.models import Q
        from rest_framework.pagination import PageNumberPagination
        from organizations.models import EmployeeProfile
        from organizations.access_summary import employee_access_summary
        from organizations.access_projection import position_access_projection
        from organizations.serializers import EmployeeAccessChangeSerializer
        position = get_object_or_404(Position, pk=pk, company=request.user.company, is_active=True)
        data = PositionAccessInput(data=request.data)
        data.is_valid(raise_exception=True)
        capabilities, scope = validate_position_access(actor=request.user, position=position, values=data.validated_data)
        profiles = EmployeeProfile.objects.filter(company=request.user.company, user__company=request.user.company,
            user__is_deleted=False).filter(Q(position=position) | Q(position_assignments__position=position,
            position_assignments__company=request.user.company, position_assignments__is_active=True)).distinct().select_related(
            'user__company', 'position__branch', 'branch').order_by('user__full_name', 'pk')
        pager = PageNumberPagination()
        pager.page_size = 25
        page = pager.paginate_queryset(profiles, request, view=self)
        results = [{'employee_name': profile.user.full_name,
                    'before': employee_access_summary(profile),
                    'after': position_access_projection(profile, position, capabilities, scope)} for profile in page]
        return pager.get_paginated_response(EmployeeAccessChangeSerializer(results, many=True).data)
