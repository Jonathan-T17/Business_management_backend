from django.db import models, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.roles import Roles
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from security.services import create_audit_log
from notifications.services import CommunicationService

from companies.models import Branch
from users.models import User

from .models import (
    Department,
    Team,
    Position,
    EmployeeProfile,
    EmployeeTransfer,
    EmployeeNote,
    EmployeeDelegation,
    EmployeeReplacement,
    EmployeeCompensation,
    UserCapabilityGrant,
    PositionCapabilityGrant,
)

from .serializers import (
    DepartmentSerializer,
    TeamSerializer,
    PositionSerializer,
    EmployeeProfileSerializer,
    EmployeeDirectorySerializer,
    EmployeeDirectoryOverviewSerializer,
    EmployeeAccessSummarySerializer,
    PrimaryPositionPreviewInputSerializer,
    EmployeeAccessChangeSerializer,
    EmployeeTransferSerializer,
    EmployeeNoteSerializer,
    EmployeeDelegationSerializer,
    EmployeeReplacementSerializer,
    EmployeeCompensationSerializer,
    UserCapabilityGrantSerializer,
    PositionCapabilityGrantSerializer,
)

from .services import (
    DelegationService,
    EmployeeLifecycleService,
    EmployeeReplacementService,
    EmployeeService,
    CompensationService,
    CapabilityGrantService,
)

from .permissions import (
    OrganizationPermission,
    CanManageOrganization,
    IsOrganizationAdmin,
    IsOrganizationManager,
    CanViewOrganization,
    CanManageEmployees,
    CanViewCompensation,
    CanManageCompensation,
)


# ============================================================
# Base Organization ViewSet
# ============================================================

class OrganizationBaseViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for organization resources.

    Provides:
    - authentication
    - organization permission checking
    - company isolation
    - role-aware queryset filtering
    - common audit logging
    """

    permission_classes = [
        IsAuthenticated,
        OrganizationPermission,
    CanManageOrganization,
    ]

    # --------------------------------------------------------
    # User helpers
    # --------------------------------------------------------

    def get_company(self):
        return getattr(self.request.user, "company", None)

    def is_admin(self):
        return self.request.user.role == Roles.ADMIN

    def is_manager(self):
        return self.request.user.role == Roles.MANAGER

    def is_employee(self):
        return self.request.user.role == Roles.EMPLOYEE

    # --------------------------------------------------------
    # Company validation
    # --------------------------------------------------------

    def require_company(self):
        """Require a tenant identity before company-dependent mutations."""
        if not CapabilityService.is_tenant_identity(self.request.user):
            raise PermissionDenied("A tenant account is required.")

        company = self.get_company()

        if company is None:
            raise PermissionDenied(
                "This operation requires a company context."
            )

        return company

    # --------------------------------------------------------
    # Audit logging
    # --------------------------------------------------------

    def perform_destroy(self, instance):
        user = self.request.user

        create_audit_log(
            user=user,
            request=self.request,
            action="DELETE",
            description=(
                f"{instance.__class__.__name__} deleted: "
                f"{str(instance)}"
            ),
            obj=instance,
        )

        instance.delete()


# ============================================================
# Department
# ============================================================

class DepartmentViewSet(OrganizationBaseViewSet):
    """
    Department management.

    Hierarchy:

        Company / Head Office
                |
              Branch
                |
            Department
    """

    serializer_class = DepartmentSerializer

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = Department.objects.select_related(
            "company",
            "branch",
            "manager",
            "created_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(
            company_id=user.company_id
        )

        if user.role in (
            Roles.MANAGER,
            Roles.EMPLOYEE,
        ):
            queryset = queryset.filter(
                branch_id=user.branch_id
            )

        return queryset

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanViewOrganization(),
            ]

        return [
            IsAuthenticated(),
            CanManageOrganization(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):
        company = self.require_company()

        department = serializer.save(
            company=company,
            created_by=self.request.user,
        )

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="CREATE",
            description=(
                f"Department created: {department.name}"
            ),
            obj=department,
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):
        department = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Department updated: {department.name}"
            ),
            obj=department,
        )


# ============================================================
# Team
# ============================================================

class TeamViewSet(OrganizationBaseViewSet):
    """
    Team management.

    Hierarchy:

        Company / Head Office
                |
              Branch
                |
            Department
                |
               Team
    """

    serializer_class = TeamSerializer

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = Team.objects.select_related(
            "company",
            "branch",
            "department",
            "leader",
            "created_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(
            company_id=user.company_id
        )

        if user.role in (
            Roles.MANAGER,
            Roles.EMPLOYEE,
        ):
            queryset = queryset.filter(
                branch_id=user.branch_id
            )

        return queryset

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanViewOrganization(),
            ]

        return [
            IsAuthenticated(),
            CanManageOrganization(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):
        company = self.require_company()

        team = serializer.save(
            company=company,
            created_by=self.request.user,
        )

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="CREATE",
            description=f"Team created: {team.name}",
            obj=team,
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):
        team = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=f"Team updated: {team.name}",
            obj=team,
        )


# ============================================================
# Position
# ============================================================

class PositionViewSet(OrganizationBaseViewSet):
    """
    Company-wide position/job-title management.
    """

    serializer_class = PositionSerializer

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = Position.objects.select_related(
            "company",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        if self.action in ("update", "partial_update"):
            queryset = queryset.select_for_update(of=("self",))
        return queryset

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Serialize structural edits with access reviews so a stale model save
        # cannot restore a scope that another administrator just changed.
        return super().update(request, *args, **kwargs)

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanViewOrganization(),
            ]

        return [
            IsAuthenticated(),
            CanManageOrganization(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):
        company = self.require_company()

        position = serializer.save(
            company=company,
            primary_scope="BRANCH" if serializer.validated_data.get("branch") else "COMPANY",
        )

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="CREATE",
            description=(
                f"Position created: {position.title}"
            ),
            obj=position,
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):
        position = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Position updated: {position.title}"
            ),
            obj=position,
        )


# ============================================================
# Employee Profile
# ============================================================

class EmployeeProfileViewSet(OrganizationBaseViewSet):
    """
    Employee management.

    Organization hierarchy:

        Company / Head Office
                |
              Branch
                |
            Department
                |
               Team
                |
             Employee
    """

    serializer_class = EmployeeProfileSerializer

    # Search is applied after the tenant/branch queryset restrictions below.
    search_fields = ("user__full_name", "user__email", "employee_id")
    ordering = ("user__full_name", "id")
    filterset_fields = ("branch", "department", "team", "position", "status")

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeDirectorySerializer
        if self.action == "overview":
            return EmployeeDirectoryOverviewSerializer
        if self.action == "access_summary":
            return EmployeeAccessSummarySerializer
        return EmployeeProfileSerializer

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = EmployeeProfile.objects.select_related(
            "user",
            "company",
            "branch",
            "department",
            "team",
            "manager",
            "position",
        )

        from .directory import directory_queryset
        return directory_queryset(user, queryset)

    @action(detail=False, methods=["get"])
    def overview(self, request):
        from django.db.models import Count, Q
        from django.utils import timezone
        from companies.models import CompanyInvite
        from .directory import directory_scope

        scope, branch_ids = directory_scope(request.user)
        profiles = self.get_queryset()
        counts = profiles.aggregate(
            total_profiles=Count("id"),
            current_employees=Count("id", filter=~Q(status="TERMINATED")),
            active=Count("id", filter=Q(status="ACTIVE")),
            on_leave=Count("id", filter=Q(status="ON_LEAVE")),
            suspended=Count("id", filter=Q(status="SUSPENDED")),
            terminated=Count("id", filter=Q(status="TERMINATED")),
            awaiting_position=Count("id", filter=~Q(status="TERMINATED") & (Q(position__isnull=True) | Q(position__is_active=False))),
        )
        rows = profiles.values("branch_id").annotate(
            total=Count("id"), current=Count("id", filter=~Q(status="TERMINATED")),
            active=Count("id", filter=Q(status="ACTIVE")),
            on_leave=Count("id", filter=Q(status="ON_LEAVE")),
            suspended=Count("id", filter=Q(status="SUSPENDED")),
            terminated=Count("id", filter=Q(status="TERMINATED")),
        ).order_by()
        by_branch = {row["branch_id"]: row for row in rows}
        offices = Branch.objects.filter(company_id=request.user.company_id)
        if scope != "COMPANY":
            # Include the caller's profile location only when that row is visible.
            offices = offices.filter(pk__in=set(branch_ids) | set(key for key in by_branch if key is not None))
        branches = []
        for office in offices.order_by("name", "id"):
            row = by_branch.get(office.pk, {})
            branches.append({"id": office.pk, "name": office.name, **{key: row.get(key, 0) for key in ("total", "current", "active", "on_leave", "suspended", "terminated")}})
        if None in by_branch:
            branches.append({"id": None, "name": "No branch recorded", **{key: value for key, value in by_branch[None].items() if key != "branch_id"}})
        accounts = User.objects.filter(company_id=request.user.company_id, is_deleted=False, is_superuser=False).exclude(role=Roles.SUPERUSER)
        return Response(self.get_serializer({
            "scope": scope, **counts, "branches": branches,
            "workspace_accounts": accounts.count() if scope == "COMPANY" else None,
            "accounts_without_profile": accounts.filter(employee_profile__isnull=True).count() if scope == "COMPANY" else None,
            "pending_invitations": CompanyInvite.objects.filter(company_id=request.user.company_id, status="PENDING", expires_at__gt=timezone.now()).count() if scope == "COMPANY" else None,
            "self_profile_id": profiles.filter(user=request.user).values_list("id", flat=True).first(),
        }).data)

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):
        if self.action == "require_password_reset":
            return [
                IsAuthenticated(),
                IsOrganizationAdmin(),
            ]

        if self.action in {"assign_position", "access_summary", "preview_position"}:
            from company_setup.permissions import IsCompanySetupAdmin
            return [IsAuthenticated(), CanManageEmployees(), IsCompanySetupAdmin()]

        if self.action in (
            "list",
            "retrieve",
            "overview",
        ):
            return [
                IsAuthenticated(),
                CanViewOrganization(),
            ]

        return [
            IsAuthenticated(),
            CanManageEmployees(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="access-summary")
    def access_summary(self, request, pk=None):
        from .access_summary import employee_access_summary
        return Response(self.get_serializer(employee_access_summary(self.get_object())).data)

    def perform_create(self, serializer):
        company = self.require_company()

        profile = serializer.save(
            company=company,
        )

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="CREATE",
            description=(
                f"Employee profile created: "
                f"{profile.user.email}"
            ),
            obj=profile,
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):
        profile = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Employee profile updated: "
                f"{profile.user.email}"
            ),
            obj=profile,
        )

    # ========================================================
    # Suspend Employee
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="suspend",
    )
    def suspend(self, request, pk=None):
        profile = self.get_object()

        reason = request.data.get("reason", "").strip()

        EmployeeService.suspend_employee(
            profile=profile,
            reason=reason,
            request=request,
        )

        profile.refresh_from_db()

        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Employee suspended",
            message="Your employment status has been changed to suspended.",
            reference_id=str(profile.id),
            url=f"/employees/{profile.id}",
            send_email=True,
            email_subject="Employment status updated",
            email_template="emails/organization_update.html",
            email_context={
                "profile": profile,
                "reason": reason,
            },
        )
        return Response(
            {
                "message": (
                    "Employee suspended successfully."
                ),
                "employee_id": profile.employee_id,
                "status": profile.status,
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Activate Employee
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    def activate(self, request, pk=None):
        profile = self.get_object()

        EmployeeService.activate_employee(
            profile=profile,
            request=request,
        )

        profile.refresh_from_db()

        # Notify employee of activation
        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Employee activated",
            message="Your employment status has been changed to active.",
            reference_id=str(profile.id),
            url=f"/employees/{profile.id}",
            send_email=True,
            email_subject="Employment status updated",
            email_template="emails/organization_update.html",
            email_context={
                "profile": profile,
            },
        )
        return Response(
            {
                "message": (
                    "Employee activated successfully."
                ),
                "employee_id": profile.employee_id,
                "status": profile.status,
            },
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Terminate Employee
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="terminate",
    )
    def terminate(self, request, pk=None):
        profile = self.get_object()

        reason = request.data.get(
            "reason",
            "",
        )

        if not reason:
            return Response(
                {
                    "reason": (
                        "Termination reason is required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmployeeLifecycleService.terminate(
            profile=profile,
            reason=reason,
            request=request,
        )
        return Response(
            {
                "message": "Employment terminated.",
                "employee_id": profile.employee_id,
                "status": profile.status,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="leave")
    def place_on_leave(self, request, pk=None):
        profile = self.get_object()

        EmployeeLifecycleService.place_on_leave(
            profile=profile,
            reason=request.data.get("reason", ""),
            request=request,
        )

        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], url_path="return-from-leave")
    def return_from_leave(self, request, pk=None):
        profile = self.get_object()

        EmployeeLifecycleService.return_from_leave(
            profile=profile,
            request=request,
        )

        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=["post"], url_path="require-password-reset")
    def require_password_reset(self, request, pk=None):
        profile = self.get_object()
        reason = request.data.get("reason", "").strip()

        if not reason:
            return Response(
                {"reason": "A reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmployeeLifecycleService.require_password_reset(
            user=profile.user,
            reason=reason,
            request=request,
        )

        return Response({
            "message": "Password reset requirement applied."
        })

    @action(detail=True, methods=["post"], url_path="replace")
    def replace_employee(self, request, pk=None):
        outgoing = self.get_object()
        incoming_id = request.data.get("incoming_employee")

        if not incoming_id:
            return Response(
                {"incoming_employee": "Incoming employee is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            incoming = EmployeeProfile.objects.get(
                id=incoming_id,
                company=outgoing.company,
            )
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"incoming_employee": "Invalid incoming employee."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        replacement = EmployeeReplacementService.execute(
            outgoing=outgoing,
            incoming=incoming,
            transfer_open_tasks=request.data.get("transfer_open_tasks", True),
            transfer_project_memberships=request.data.get(
                "transfer_project_memberships", True
            ),
            transfer_team_leadership=request.data.get(
                "transfer_team_leadership", False
            ),
            transfer_department_management=request.data.get(
                "transfer_department_management", False
            ),
            transfer_branch_management=request.data.get(
                "transfer_branch_management", False
            ),
            reason=request.data.get("reason", ""),
            performed_by=request.user,
            request=request,
        )

        return Response(
            EmployeeReplacementSerializer(
                replacement,
                context={"request": request},
            ).data
        )

    # ========================================================
    # Assign Department
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-department",
    )
    def assign_department(self, request, pk=None):
        profile = self.get_object()

        department_id = request.data.get(
            "department"
        )

        if not department_id:
            return Response(
                {
                    "department":
                    "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        department = get_object_or_404(
            Department,
            id=department_id,
            company_id=profile.company_id,
        )

        if (
            request.user.role == Roles.MANAGER
            and department.branch_id != request.user.branch_id
        ):
            raise PermissionDenied(
                "You cannot assign an employee to "
                "a department outside your branch."
            )

        if (
            profile.branch_id
            and department.branch_id != profile.branch_id
        ):
            return Response(
                {
                    "department":
                    "Department must belong to "
                    "the employee's branch."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmployeeService.assign_department(
            profile=profile,
            department=department,
            request=request,
        )

        profile.refresh_from_db()

        return Response(
            EmployeeProfileSerializer(
                profile,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Assign Team
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-team",
    )
    def assign_team(self, request, pk=None):
        profile = self.get_object()

        team_id = request.data.get(
            "team"
        )

        if not team_id:
            return Response(
                {
                    "team":
                    "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        team = get_object_or_404(
            Team,
            id=team_id,
            company_id=profile.company_id,
        )

        if (
            request.user.role == Roles.MANAGER
            and team.branch_id != request.user.branch_id
        ):
            raise PermissionDenied(
                "You cannot assign an employee to "
                "a team outside your branch."
            )

        if (
            profile.branch_id
            and team.branch_id != profile.branch_id
        ):
            return Response(
                {
                    "team":
                    "Team must belong to "
                    "the employee's branch."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            profile.department_id
            and team.department_id != profile.department_id
        ):
            return Response(
                {
                    "team":
                    "Team must belong to "
                    "the employee's department."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmployeeService.assign_team(
            profile=profile,
            team=team,
            request=request,
        )

        profile.refresh_from_db()

        return Response(
            EmployeeProfileSerializer(
                profile,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Assign Manager
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-manager",
    )
    def assign_manager(self, request, pk=None):
        profile = self.get_object()

        manager_id = request.data.get(
            "manager"
        )

        if not manager_id:
            return Response(
                {
                    "manager":
                    "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        manager = get_object_or_404(
            User,
            id=manager_id,
            company_id=profile.company_id,
        )

        if manager.id == profile.user_id:
            return Response(
                {
                    "manager":
                    "An employee cannot be their own manager."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            request.user.role == Roles.MANAGER
            and manager.branch_id != request.user.branch_id
        ):
            raise PermissionDenied(
                "You cannot assign a manager "
                "from another branch."
            )

        if (
            profile.branch_id
            and manager.branch_id != profile.branch_id
        ):
            return Response(
                {
                    "manager":
                    "Manager must belong to "
                    "the employee's branch."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        EmployeeService.assign_manager(
            profile=profile,
            manager=manager,
            request=request,
        )

        profile.refresh_from_db()

        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Manager assigned",
            message=f"You have been assigned a new manager: {manager.get_full_name()}",
            reference_id=str(profile.id),
            url=f"/employees/{profile.id}",
            send_email=True,
            email_subject="Manager assignment updated",
            email_template="emails/organization_update.html",
            email_context={
                "profile": profile,
                "manager": manager,
            },
        )
        return Response(
            EmployeeProfileSerializer(
                profile,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Assign Position
    # ========================================================

    @extend_schema(request=PrimaryPositionPreviewInputSerializer, responses=EmployeeAccessChangeSerializer)
    @action(detail=True, methods=["post"], url_path="preview-position")
    def preview_position(self, request, pk=None):
        from .access_projection import primary_position_projection
        from .access_summary import employee_access_summary
        profile = self.get_object()
        data = PrimaryPositionPreviewInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        position = get_object_or_404(Position, pk=data.validated_data['position'], company_id=profile.company_id)
        EmployeeService.validate_position_assignment(profile=profile, position=position, request=request)
        return Response(EmployeeAccessChangeSerializer({
            'employee_name': profile.user.full_name,
            'before': employee_access_summary(profile),
            'after': primary_position_projection(profile, position),
        }).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="assign-position",
    )
    def assign_position(self, request, pk=None):
        profile = self.get_object()

        position_id = request.data.get(
            "position"
        )

        if not position_id:
            return Response(
                {
                    "position":
                    "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        position = get_object_or_404(
            Position,
            id=position_id,
            company_id=profile.company_id,
        )

        EmployeeService.assign_position(
            profile=profile,
            position=position,
            request=request,
        )

        profile.refresh_from_db()

        return Response(
            EmployeeProfileSerializer(
                profile,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )

    # ========================================================
    # Transfer Employee
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="transfer",
    )
    def transfer(self, request, pk=None):
        profile = self.get_object()

        new_branch_id = request.data.get(
            "branch"
        )
        new_department_id = request.data.get(
            "department"
        )
        new_team_id = request.data.get(
            "team"
        )
        reason = request.data.get(
            "reason",
            "",
        )

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        if not new_branch_id:
            return Response(
                {
                    "branch":
                    "New branch is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_department_id:
            return Response(
                {
                    "department":
                    "New department is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_team_id:
            return Response(
                {
                    "team":
                    "New team is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reason:
            return Response(
                {
                    "reason":
                    "Transfer reason is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # New branch
        # ----------------------------------------------------

        branch = get_object_or_404(
            Branch,
            id=new_branch_id,
            company_id=profile.company_id,
        )

        # ----------------------------------------------------
        # Manager branch restriction
        # ----------------------------------------------------

        if (
            request.user.role == Roles.MANAGER
            and branch.id != request.user.branch_id
        ):
            raise PermissionDenied(
                "Managers cannot transfer employees "
                "to another branch."
            )

        # ----------------------------------------------------
        # New department
        # ----------------------------------------------------

        department = get_object_or_404(
            Department,
            id=new_department_id,
            company_id=profile.company_id,
        )

        if department.branch_id != branch.id:
            return Response(
                {
                    "department":
                    "Department must belong to "
                    "the new branch."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # New team
        # ----------------------------------------------------

        team = get_object_or_404(
            Team,
            id=new_team_id,
            company_id=profile.company_id,
        )

        if team.branch_id != branch.id:
            return Response(
                {
                    "team":
                    "Team must belong to "
                    "the new branch."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if team.department_id != department.id:
            return Response(
                {
                    "team":
                    "Team must belong to "
                    "the selected department."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Prevent unnecessary transfer
        # ----------------------------------------------------

        if (
            profile.branch_id == branch.id
            and profile.department_id == department.id
            and profile.team_id == team.id
        ):
            return Response(
                {
                    "detail":
                    "Employee is already assigned "
                    "to this branch, department and team."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Perform transfer
        # ----------------------------------------------------

        EmployeeService.transfer_employee(
            profile=profile,
            new_branch=branch,
            new_department=department,
            new_team=team,
            approved_by=request.user,
            reason=reason,
            request=request,
        )
        
        profile.refresh_from_db()
        
        # Notify employee of transfer
        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Organization assignment updated",
            message="Your branch, department or team assignment has been updated.",
            reference_id=str(profile.id),
            url=f"/employees/{profile.id}",
            send_email=True,
            email_subject="Organization assignment updated",
            email_template="emails/organization_update.html",
            email_context={
                "profile": profile,
                "transfer_reason": reason,
            },
        )

        return Response(
            EmployeeProfileSerializer(
                profile,
                context={"request": request},
            ).data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# Employee Delegations
# ============================================================

class EmployeeDelegationViewSet(viewsets.ModelViewSet):

    serializer_class = EmployeeDelegationSerializer

    permission_classes = [
        IsAuthenticated,
        IsOrganizationManager,
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = EmployeeDelegation.objects.select_related(
            "company",
            "from_user",
            "to_user",
            "created_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(company=user.company)

        if self.request.query_params.get("delegator"):
            queryset = queryset.filter(from_user__employee_profile__id=self.request.query_params["delegator"])

        if user.role == Roles.ADMIN:
            return queryset

        return queryset.filter(
            models.Q(from_user=user)
            | models.Q(to_user=user)
        )

    def perform_create(self, serializer):
        data = serializer.validated_data

        delegation = DelegationService.create(
            from_user=data["from_user"],
            to_user=data["to_user"],
            permissions=data.get("permissions", []),
            starts_at=data["starts_at"],
            ends_at=data["ends_at"],
            reason=data.get("reason", ""),
            created_by=self.request.user,
            request=self.request,
        )

        serializer.instance = delegation


# ============================================================
# Employee Compensation
# ============================================================

class EmployeeCompensationViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = EmployeeCompensationSerializer
    permission_classes = [IsAuthenticated, CanViewCompensation]

    def get_queryset(self):
        user = self.request.user
        queryset = EmployeeCompensation.objects.select_related(
            "employee",
            "employee__user",
            "company",
            "created_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(company=user.company)
        if self.request.query_params.get("employee"):
            queryset = queryset.filter(employee_id=self.request.query_params["employee"])
        if self.request.query_params.get("is_current") == "true":
            queryset = queryset.filter(is_current=True)
        return queryset

    @action(
        detail=False,
        methods=["post"],
        url_path="set",
        permission_classes=[IsAuthenticated, CanManageCompensation],
    )
    def set_compensation(self, request):
        employee_id = request.data.get("employee")

        if not employee_id:
            return Response(
                {"employee": "Employee is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        employee_lookup = {"id": employee_id, "company": request.user.company}

        try:
            employee = EmployeeProfile.objects.get(**employee_lookup)
        except EmployeeProfile.DoesNotExist:
            return Response(
                {"employee": "Invalid employee."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required = ("base_salary", "currency", "effective_from")
        missing = [
            field for field in required
            if request.data.get(field) in (None, "")
        ]
        if missing:
            return Response(
                {field: "This field is required." for field in missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        compensation = CompensationService.set_compensation(
            employee=employee,
            base_salary=request.data["base_salary"],
            currency=request.data["currency"],
            effective_from=request.data["effective_from"],
            housing_allowance=request.data.get("housing_allowance", 0),
            transport_allowance=request.data.get("transport_allowance", 0),
            other_allowance=request.data.get("other_allowance", 0),
            notes=request.data.get("notes", ""),
            user=request.user,
            request=request,
        )

        return Response(
            self.get_serializer(compensation).data,
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# User Capability Grants
# ============================================================

class UserCapabilityGrantViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = UserCapabilityGrantSerializer
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = UserCapabilityGrant.objects.select_related(
            "company",
            "user",
            "granted_by",
            "revoked_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(company=user.company)
        if self.request.query_params.get("user"):
            queryset = queryset.filter(user_id=self.request.query_params["user"])
        return queryset

    @action(detail=False, methods=["post"], url_path="grant")
    def grant(self, request):
        user_id = request.data.get("user")
        capability = request.data.get("capability")

        if not user_id:
            raise ValidationError({"user": "User is required."})

        if capability not in Capabilities.values():
            raise ValidationError({"capability": "Invalid capability."})

        try:
            target_user = User.objects.get(
                id=user_id,
                company=request.user.company,
            )
        except User.DoesNotExist:
            raise ValidationError({"user": "Invalid user."})

        try:
            grant = CapabilityGrantService.grant_user(
                company=request.user.company,
                target_user=target_user,
                capability=capability,
                actor=request.user,
                reason=request.data.get("reason", ""),
                request=request,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages)

        return Response(self.get_serializer(grant).data)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        grant = self.get_object()

        CapabilityGrantService.revoke_user(
            grant=grant,
            actor=request.user,
            reason=request.data.get("reason", ""),
            request=request,
        )

        return Response({"message": "Capability revoked."})


class PositionCapabilityGrantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PositionCapabilityGrantSerializer
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get_queryset(self):
        queryset = PositionCapabilityGrant.objects.select_related(
            "company",
            "position",
            "granted_by",
        )
        if not CapabilityService.is_tenant_identity(self.request.user):
            return queryset.none()
        return queryset.filter(company=self.request.user.company)

    @action(detail=False, methods=["post"], url_path="grant")
    def grant(self, request):
        position_id = request.data.get("position")
        capability = request.data.get("capability")

        if not position_id:
            raise ValidationError({"position": "Position is required."})
        if capability not in Capabilities.values():
            raise ValidationError({"capability": "Invalid capability."})

        try:
            position = Position.objects.get(
                id=position_id,
                company=request.user.company,
            )
        except Position.DoesNotExist:
            raise ValidationError({"position": "Invalid position."})

        try:
            grant = CapabilityGrantService.grant_position(
                company=request.user.company,
                position=position,
                capability=capability,
                actor=request.user,
                reason=request.data.get("reason", ""),
                request=request,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response(self.get_serializer(grant).data)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        grant = self.get_object()
        grant.is_active = False
        grant.save(update_fields=["is_active"])
        create_audit_log(
            user=request.user,
            company=grant.company,
            request=request,
            action="SECURITY",
            description=(
                f"Capability {grant.capability} revoked from "
                f"position {grant.position.title}."
            ),
            obj=grant,
        )
        return Response({"message": "Capability revoked."})


class CapabilityCatalogueView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def get(self, request):
        return Response({
            "capabilities": Capabilities.catalogue(),
            "presets": [
                {
                    "code": code,
                    "name": code.replace("_", " ").title(),
                    "capabilities": capabilities,
                }
                for code, capabilities in Capabilities.PRESETS.items()
            ],
        })


class RolePresetView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationAdmin]

    def post(self, request):
        position_id = request.data.get("position")
        preset = request.data.get("preset")

        if preset not in Capabilities.PRESETS:
            raise ValidationError({"preset": "Invalid role preset."})

        try:
            position = Position.objects.get(
                id=position_id,
                company=request.user.company,
            )
        except Position.DoesNotExist:
            raise ValidationError({"position": "Invalid position."})

        grants = [
            CapabilityGrantService.grant_position(
                company=request.user.company,
                position=position,
                capability=capability,
                actor=request.user,
                reason=f"Applied {preset.replace('_', ' ').title()} preset.",
                request=request,
            )
            for capability in Capabilities.PRESETS[preset]
        ]
        return Response({
            "preset": preset,
            "position": str(position.id),
            "grants": PositionCapabilityGrantSerializer(
                grants,
                many=True,
            ).data,
        })


# ============================================================
# Employee Transfer History
# ============================================================

class EmployeeTransferViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """
    Read-only employee transfer history.

    Visibility:

    SUPERUSER
        All transfers.

    ADMIN
        All transfers within company.

    MANAGER
        Transfers belonging to their branch.

    EMPLOYEE
        Their own transfer history.
    """

    serializer_class = EmployeeTransferSerializer

    def get_permissions(self):
        return [
            IsAuthenticated(),
            CanViewOrganization(),
        ]

    def get_queryset(self):
        user = self.request.user

        queryset = EmployeeTransfer.objects.select_related(
            "employee",
            "employee__user",
            "employee__company",
            "employee__branch",
            "old_branch",
            "new_branch",
            "old_department",
            "new_department",
            "old_team",
            "new_team",
            "approved_by",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(
            employee__company_id=user.company_id
        )

        if user.role == Roles.ADMIN:
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(
                employee__branch_id=user.branch_id
            )

        if user.role == Roles.EMPLOYEE:
            return queryset.filter(
                employee__user_id=user.id
            )

        return queryset.none()


# ============================================================
# Employee Notes
# ============================================================

class EmployeeNoteViewSet(
    viewsets.ModelViewSet
):
    """
    Employee notes.

    Notes are visible according to organization scope.

    Employees can view their own notes but cannot create,
    update or delete notes.
    """

    serializer_class = EmployeeNoteSerializer

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    def get_permissions(self):
        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanViewOrganization(),
            ]

        return [
            IsAuthenticated(),
            CanManageEmployees(),
        ]

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = EmployeeNote.objects.select_related(
            "employee",
            "employee__user",
            "employee__company",
            "employee__branch",
            "employee__department",
            "employee__team",
            "author",
        )

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(
            employee__company_id=user.company_id
        )

        if user.role == Roles.ADMIN:
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(
                employee__branch_id=user.branch_id
            )

        if user.role == Roles.EMPLOYEE:
            return queryset.filter(
                employee__user_id=user.id
            )

        return queryset.none()

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):
        employee = serializer.validated_data["employee"]

        user = self.request.user

        # Company isolation
        if (
            not CapabilityService.is_tenant_identity(user)
            or employee.company_id != user.company_id
        ):
            raise PermissionDenied(
                "You cannot add a note to an employee "
                "outside your company."
            )

        # Manager branch isolation
        if (
            user.role == Roles.MANAGER
            and employee.branch_id != user.branch_id
        ):
            raise PermissionDenied(
                "You cannot add notes to employees "
                "outside your branch."
            )

        note = serializer.save(
            author=user
        )

        create_audit_log(
            user=user,
            request=self.request,
            action="CREATE",
            description=(
                f"Employee note created for "
                f"{employee.user.email}"
            ),
            obj=note,
        )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def perform_update(self, serializer):
        note = serializer.save()

        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="UPDATE",
            description=(
                f"Employee note updated for "
                f"{note.employee.user.email}"
            ),
            obj=note,
        )

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    def perform_destroy(self, instance):
        create_audit_log(
            user=self.request.user,
            request=self.request,
            action="DELETE",
            description=(
                f"Employee note deleted for "
                f"{instance.employee.user.email}"
            ),
            obj=instance,
        )

        instance.delete()
