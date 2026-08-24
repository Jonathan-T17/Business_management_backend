from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles
from security.services import create_audit_log
from notifications.services import create_notification

from .models import (Company, Branch, CompanyInvite)

from .serializers import (CompanySerializer, BranchSerializer, CompanyInviteSerializer)

from .permissions import (
    IsCompanyMember, IsCompanyAdmin,
    CanManageBranches, CanManageInvites)

from .services import CompanyInviteService

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .serializers import PublicInviteSerializer
from django.conf import settings



class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Company.objects.none()

        if user.role == Roles.SUPERUSER:
            return Company.objects.all()

        if not getattr(user, "company_id", None):
            return Company.objects.none()

        return Company.objects.filter(
            pk=user.company_id
        )

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                IsCompanyMember(),
            ]

        return [
            IsAuthenticated(),
            IsCompanyAdmin(),
        ]

    def create(self, request, *args, **kwargs):
        """
        Normal company creation is handled by the registration/
        onboarding workflow.

        This endpoint is intentionally restricted to superusers.
        """

        if request.user.role != Roles.SUPERUSER:
            raise PermissionDenied(
                "Company creation must be performed through the onboarding workflow."
            )

        return super().create(
            request,
            *args,
            **kwargs,
        )

    def perform_create(self, serializer):
        company = serializer.save(
            created_by=self.request.user
        )

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="CREATE",
            description=(
                f"Company created: {company.name}"
            ),
            obj=company,
        )

    def perform_update(self, serializer):
        company = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Company updated: {company.name}"
            ),
            obj=company,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Do not expose hard company deletion through the API.
        Company deactivation is safer and preserves historical data.
        """
        raise PermissionDenied(
            "Companies cannot be permanently deleted through this endpoint. "
            "Deactivate the company instead."
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    def activate(self, request, pk=None):
        company = self.get_object()

        company.is_active = True
        company.save(update_fields=["is_active"])

        create_audit_log(
            user=request.user,
            request=request,
            action="UPDATE",
            description=(
                f"Company activated: {company.name}"
            ),
            obj=company,
        )

        return Response(
            {
                "message": "Company activated successfully.",
                "company_id": company.id,
                "is_active": company.is_active,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(self, request, pk=None):
        company = self.get_object()

        if company.id != request.user.company_id:
            if request.user.role != Roles.SUPERUSER:
                raise PermissionDenied(
                    "You cannot deactivate another company."
                )

        company.is_active = False
        company.save(update_fields=["is_active"])

        create_audit_log(
            user=request.user,
            request=request,
            action="UPDATE",
            description=(
                f"Company deactivated: {company.name}"
            ),
            obj=company,
        )

        return Response(
            {
                "message": "Company deactivated successfully.",
                "company_id": company.id,
                "is_active": company.is_active,
            }
        )


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Branch.objects.none()

        queryset = Branch.objects.select_related(
            "company",
            "manager",
            "created_by",
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        if not getattr(user, "company_id", None):
            return queryset.none()

        queryset = queryset.filter(
            company_id=user.company_id
        )

        if user.role == Roles.MANAGER:
            queryset = queryset.filter(
                pk=user.branch_id
            )

        elif user.role == Roles.EMPLOYEE:
            queryset = queryset.filter(
                pk=user.branch_id
            )

        return queryset

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                IsCompanyMember(),
            ]

        return [
            IsAuthenticated(),
            CanManageBranches(),
        ]

    def perform_create(self, serializer):
        user = self.request.user

        branch = serializer.save(
            company=user.company,
            created_by=user,
        )

        create_audit_log(
            user=user,
            request=self.request,
            action="CREATE",
            description=(
                f"Branch created: {branch.name}"
            ),
            obj=branch,
        )

    def perform_update(self, serializer):
        branch = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Branch updated: {branch.name}"
            ),
            obj=branch,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    def activate(self, request, pk=None):
        branch = self.get_object()

        branch.is_active = True
        branch.save(update_fields=["is_active"])

        create_audit_log(
            user=request.user,
            request=request,
            action="UPDATE",
            description=(
                f"Branch activated: {branch.name}"
            ),
            obj=branch,
        )

        return Response(
            {
                "message": "Branch activated successfully.",
                "branch_id": branch.id,
                "is_active": branch.is_active,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(self, request, pk=None):
        branch = self.get_object()

        branch.is_active = False
        branch.save(update_fields=["is_active"])

        create_audit_log(
            user=request.user,
            request=request,
            action="UPDATE",
            description=(
                f"Branch deactivated: {branch.name}"
            ),
            obj=branch,
        )

        return Response(
            {
                "message": "Branch deactivated successfully.",
                "branch_id": branch.id,
                "is_active": branch.is_active,
            }
        )


class CompanyInviteViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyInviteSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return CompanyInvite.objects.none()

        if user.role == Roles.SUPERUSER:
            return CompanyInvite.objects.select_related(
                "company",
                "created_by",
            )

        if not getattr(user, "company_id", None):
            return CompanyInvite.objects.none()

        return (
            CompanyInvite.objects
            .select_related(
                "company",
                "created_by",
            )
            .filter(
                company_id=user.company_id
            )
        )

    def get_permissions(self):
        if self.action == "accept":
            return [
                IsAuthenticated(),
            ]

        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                IsCompanyMember(),
            ]

        return [
            IsAuthenticated(),
            CanManageInvites(),
        ]

    def perform_create(self, serializer):
        user = self.request.user

        # ✅ Use service layer to create the invite
        invite = CompanyInviteService.create_invite(
            company=user.company,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            created_by=user,
            request=self.request,
            days_valid=serializer.validated_data.get("days_valid"),
        )

        # ✅ Attach the instance back to serializer
        serializer.instance = invite

        # ✅ Audit log
        create_audit_log(
            user=user,
            company=invite.company,
            request=self.request,
            action="CREATE",
            description=f"Company invitation created for {invite.email}",
            obj=invite,
        )

    @action(detail=True, methods=["post"], url_path="accept")

    
    @transaction.atomic
    def accept(self, request, pk=None):
        invite = (
            CompanyInvite.objects
            .select_for_update()
            .select_related("company")
            .get(pk=pk)
        )

        invite = CompanyInviteService.accept_invite(
            invite=invite,
            user=request.user,
            request=request,
        )

        create_notification(
            recipient=request.user,
            company=invite.company,
            notification_type="INVITATION",
            title="Invitation Accepted",
            message=(
                f"You have joined {invite.company.name}."
            ),
            reference_id=str(invite.id),
        )

        return Response(
            {
                "message": "Invitation accepted successfully.",
                "company_id": invite.company_id,
                "company": invite.company.name,
                "role": request.user.role,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="revoke",
    )
    def revoke(self, request, pk=None):
        invite = self.get_object()

        invite = CompanyInviteService.revoke_invite(
            invite=invite,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "message": "Invitation revoked successfully.",
                "invite_id": str(invite.id),
                "status": invite.status,
            }
        )

# public invitation
class InvitationInfoView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):

        try:
            invite = (
                CompanyInvite.objects
                .select_related("company")
                .get(token=token)
            )
        except CompanyInvite.DoesNotExist:
            return Response(
                {
                    "detail":
                    "Invitation not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not invite.is_valid:
            return Response(
                {
                    "detail":
                    "Invitation is expired, revoked, or already used."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PublicInviteSerializer(
            invite
        )

        return Response(
            serializer.data
        )


class AcceptInvitationView(APIView):
    permission_classes = [
        IsAuthenticated
    ]

    @transaction.atomic
    def post(self, request, token):

        try:
            invite = (
                CompanyInvite.objects
                .select_related("company")
                .select_for_update()
                .get(token=token)
            )
        except CompanyInvite.DoesNotExist:
            return Response(
                {
                    "detail":
                    "Invitation not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not invite.is_valid:
            return Response(
                {
                    "detail":
                    "Invitation is expired, revoked, or already accepted."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite = CompanyInviteService.accept_invite(
            invite=invite,
            user=request.user,
            request=request,
        )

        return Response(
            {
                "message":
                "Invitation accepted successfully.",
                "company_id":
                invite.company_id,
                "role":
                request.user.role,
            },
            status=status.HTTP_200_OK,
        )