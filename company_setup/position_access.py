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

class PositionAccessView(APIView):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    @extend_schema(responses=PositionAccessInput)
    def get(self, request, pk):
        position = get_object_or_404(Position, pk=pk, company=request.user.company)
        return Response({"capabilities":list(position.capability_grants.filter(company=request.user.company,is_active=True).values_list("capability",flat=True))})

    @extend_schema(request=PositionAccessInput, responses=PositionAccessInput)
    @transaction.atomic
    def put(self, request, pk):
        position = get_object_or_404(Position.objects.select_for_update(), pk=pk, company=request.user.company, is_active=True)
        data = PositionAccessInput(data=request.data)
        data.is_valid(raise_exception=True)
        capabilities = SetupCapabilityPolicy.validate_preset(actor=request.user, capabilities=data.validated_data["capabilities"])
        from core.position_scope import BRANCH_CAPABILITIES
        if position.assignments.filter(is_active=True,scope="BRANCHES").exists() and set(capabilities)-BRANCH_CAPABILITIES:
            raise serializers.ValidationError("This position has branch-limited assignments. Use a separate position for company-wide permissions.")
        PositionCapabilityGrant.objects.filter(position=position,company=request.user.company,is_active=True).exclude(capability__in=capabilities).update(is_active=False)
        for capability in capabilities:
            CapabilityGrantService.grant_position(company=request.user.company,position=position,capability=capability,actor=request.user,reason="Company setup access review",request=request)
        create_audit_log(user=request.user,company=request.user.company,request=request,action="SECURITY",description=f"Position access reviewed: {position.title}.",obj=position)
        return Response({"capabilities":capabilities})
