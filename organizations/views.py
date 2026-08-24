from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles
from security.services import create_audit_log

from companies.models import Branch
from users.models import User

from .models import (
    Department,
    Team,
    Position,
    EmployeeProfile,
    EmployeeTransfer,
    EmployeeNote,
)

from .serializers import (
    DepartmentSerializer,
    TeamSerializer,
    PositionSerializer,
    EmployeeProfileSerializer,
    EmployeeTransferSerializer,
    EmployeeNoteSerializer,
)

from .services import EmployeeService

from .permissions import (
    OrganizationPermission,
    IsOrganizationAdmin,
    CanViewOrganization,
    CanManageEmployees,
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
    ]

    # --------------------------------------------------------
    # User helpers
    # --------------------------------------------------------

    def get_company(self):
        return getattr(self.request.user, "company", None)

    def is_superuser(self):
        return self.request.user.role == Roles.SUPERUSER

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
        """
        Organization resources require a company context.

        Platform superusers may exist without being attached
        to a company, therefore company-dependent operations
        must explicitly provide a company context through the
        authenticated user or another higher-level workflow.
        """

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

        if user.role == Roles.SUPERUSER:
            return queryset

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
            IsOrganizationAdmin(),
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

        if user.role == Roles.SUPERUSER:
            return queryset

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
            IsOrganizationAdmin(),
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

        if user.role == Roles.SUPERUSER:
            return queryset

        return queryset.filter(
            company_id=user.company_id
        )

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
            IsOrganizationAdmin(),
        ]

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    def perform_create(self, serializer):
        company = self.require_company()

        position = serializer.save(
            company=company,
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

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            company_id=user.company_id
        )

        if user.role == Roles.ADMIN:
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(
                branch_id=user.branch_id
            )

        if user.role == Roles.EMPLOYEE:
            return queryset.filter(
                user_id=user.id
            )

        return queryset.none()

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
    # Create
    # --------------------------------------------------------

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

        reason = request.data.get(
            "reason",
            "",
        )

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

        EmployeeService.terminate_employee(
            profile=profile,
            reason=reason,
            request=request,
        )

        profile.refresh_from_db()

        # Notify employee of termination
        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Employment terminated",
            message="Your employment has been terminated.",
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
                    "Employee employment terminated."
                ),
                "employee_id": profile.employee_id,
                "status": profile.status,
            },
            status=status.HTTP_200_OK,
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

        if user.role == Roles.SUPERUSER:
            return queryset

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

        if user.role == Roles.SUPERUSER:
            return queryset

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
            user.role != Roles.SUPERUSER
            and employee.company_id != user.company_id
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