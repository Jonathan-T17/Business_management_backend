"""Explicit headquarters selection, without guessing from a location's name."""
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from companies.models import Branch, Company
from companies.serializers import BranchSerializer
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from security.services import create_audit_log
from subscriptions.services import SubscriptionService
from .permissions import IsCompanySetupAdmin


class HeadquartersInput(serializers.Serializer):
    branch_id = serializers.IntegerField(min_value=1, required=False)
    name = serializers.CharField(max_length=255, required=False)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        if "branch_id" in attrs:
            if "name" in attrs or "location" in attrs:
                raise serializers.ValidationError("Choose an existing location or create a new headquarters.")
        elif not attrs.get("name"):
            raise serializers.ValidationError({"name": "Enter a headquarters name or choose an existing location."})
        return attrs


class HeadquartersResult(serializers.Serializer):
    headquarters = BranchSerializer(allow_null=True, read_only=True)


class HeadquartersView(APIView):
    permission_classes = [IsAuthenticated, IsCompanySetupAdmin]

    @extend_schema(responses=HeadquartersResult)
    def get(self, request):
        company = Company.objects.select_related("headquarters").get(pk=request.user.company_id)
        return Response({"headquarters": BranchSerializer(company.headquarters).data if company.headquarters_id else None})

    @extend_schema(request=HeadquartersInput, responses=HeadquartersResult)
    @transaction.atomic
    def put(self, request):
        if not CapabilityService.has(request.user, Capabilities.MANAGE_ORGANIZATION):
            raise PermissionDenied("Company structure management authority is required.")
        data = HeadquartersInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        company = Company.objects.select_for_update().get(pk=request.user.company_id)
        if "branch_id" in values:
            branch = Branch.objects.select_for_update().filter(
                pk=values["branch_id"], company=company, is_active=True,
            ).first()
            if branch is None:
                raise ValidationError({"branch_id": "Choose an active location in your company."})
        else:
            if Branch.objects.filter(company=company, name__iexact=values["name"]).exists():
                raise ValidationError({"name": "This location already exists. Choose it from existing locations."})
            if not SubscriptionService.can_add_branch(company):
                raise ValidationError("Your plan's location limit has been reached. Choose an existing location.")
            branch = Branch.objects.create(
                company=company, name=values["name"], location=values.get("location", ""), created_by=request.user,
            )
        previous_id = company.headquarters_id
        company.headquarters = branch
        company.save(update_fields=["headquarters", "updated_at"])
        # Use the freshly saved company when serializing the location marker.
        branch.company = company
        if previous_id != branch.pk:
            create_audit_log(
                user=request.user, company=company, request=request, action="UPDATE", obj=company,
                description=f"Headquarters designated: {branch.name}.",
                metadata={"previous_headquarters_id": previous_id, "headquarters_id": branch.pk},
            )
        return Response({"headquarters": BranchSerializer(branch).data})
