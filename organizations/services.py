from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    EmployeeProfile,
    EmployeeTransfer,
    Department,
    Team,
    Position,
)

from security.services import create_audit_log


class EmployeeService:
    """
    Business logic for employee management.

    The service layer performs validation that must remain enforced
    even when the operation is called from somewhere other than
    the current API view.
    """

    # ============================================================
    # Internal Validation Helpers
    # ============================================================

    @staticmethod
    def _validate_same_company(
        *,
        company,
        branch=None,
        department=None,
        team=None,
        manager=None,
        position=None,
    ):
        if branch and branch.company_id != company.id:
            raise ValidationError(
                "Branch does not belong to the selected company."
            )

        if department and department.company_id != company.id:
            raise ValidationError(
                "Department does not belong to the selected company."
            )

        if team and team.company_id != company.id:
            raise ValidationError(
                "Team does not belong to the selected company."
            )

        if manager and manager.company_id != company.id:
            raise ValidationError(
                "Manager does not belong to the selected company."
            )

        if position and position.company_id != company.id:
            raise ValidationError(
                "Position does not belong to the selected company."
            )

    @staticmethod
    def _validate_structure(
        *,
        branch=None,
        department=None,
        team=None,
    ):
        if department and branch:
            if department.branch_id != branch.id:
                raise ValidationError(
                    "Department must belong to the selected branch."
                )

        if team and department:
            if team.department_id != department.id:
                raise ValidationError(
                    "Team must belong to the selected department."
                )

        if team and branch:
            if team.branch_id != branch.id:
                raise ValidationError(
                    "Team must belong to the selected branch."
                )

    # ============================================================
    # Create Employee Profile
    # ============================================================

    @staticmethod
    @transaction.atomic
    def create_profile(
        *,
        user,
        employee_id,
        company,
        branch=None,
        department=None,
        team=None,
        manager=None,
        position=None,
        employment_type="FULL_TIME",
        hire_date=None,
        phone="",
        office_location="",
        emergency_contact="",
        notes="",
        request=None,
    ):
        if EmployeeProfile.objects.filter(
            employee_id=employee_id
        ).exists():
            raise ValidationError(
                "Employee ID already exists."
            )

        if user.company_id != company.id:
            raise ValidationError(
                "User does not belong to the selected company."
            )

        EmployeeService._validate_same_company(
            company=company,
            branch=branch,
            department=department,
            team=team,
            manager=manager,
            position=position,
        )

        EmployeeService._validate_structure(
            branch=branch,
            department=department,
            team=team,
        )

        profile = EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            company=company,
            branch=branch,
            department=department,
            team=team,
            manager=manager,
            position=position,
            employment_type=employment_type,
            hire_date=hire_date or timezone.now().date(),
            phone=phone,
            office_location=office_location,
            emergency_contact=emergency_contact,
            notes=notes,
        )

        # Keep the User branch synchronized with the employee profile.
        if hasattr(user, "branch_id") and user.branch_id != (
            branch.id if branch else None
        ):
            user.branch = branch
            user.save(update_fields=["branch"])

        create_audit_log(
            user=request.user if request else user,
            request=request,
            action="CREATE",
            description=(
                f"Employee profile created ({user.email})"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Assign Department
    # ============================================================

    @staticmethod
    @transaction.atomic
    def assign_department(
        *,
        profile,
        department,
        request=None,
    ):
        if department.company_id != profile.company_id:
            raise ValidationError(
                "Department does not belong to the employee's company."
            )

        if profile.branch_id and department.branch_id != profile.branch_id:
            raise ValidationError(
                "Department must belong to the employee's branch."
            )

        if profile.team_id:
            if profile.team.department_id != department.id:
                raise ValidationError(
                    "The employee's current team belongs to another department."
                )

        profile.department = department
        profile.save(update_fields=["department", "updated_at"])

        create_audit_log(
            user=request.user if request else profile.user,
            request=request,
            action="UPDATE",
            description=(
                f"Department changed to {department.name}"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Assign Team
    # ============================================================

    @staticmethod
    @transaction.atomic
    def assign_team(
        *,
        profile,
        team,
        request=None,
    ):
        if team.company_id != profile.company_id:
            raise ValidationError(
                "Team does not belong to the employee's company."
            )

        if profile.branch_id and team.branch_id != profile.branch_id:
            raise ValidationError(
                "Team must belong to the employee's branch."
            )

        if profile.department_id and team.department_id != profile.department_id:
            raise ValidationError(
                "Team must belong to the employee's department."
            )

        profile.team = team
        profile.save(update_fields=["team", "updated_at"])

        create_audit_log(
            user=request.user if request else profile.user,
            request=request,
            action="UPDATE",
            description=(
                f"Assigned to team {team.name}"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Assign Manager
    # ============================================================

    @staticmethod
    @transaction.atomic
    def assign_manager(
        *,
        profile,
        manager,
        request=None,
    ):
        if manager.company_id != profile.company_id:
            raise ValidationError(
                "Manager does not belong to the employee's company."
            )

        if profile.branch_id:
            if manager.branch_id != profile.branch_id:
                raise ValidationError(
                    "Manager must belong to the employee's branch."
                )

        if manager.id == profile.user_id:
            raise ValidationError(
                "An employee cannot be their own manager."
            )

        profile.manager = manager
        profile.save(update_fields=["manager", "updated_at"])

        create_audit_log(
            user=request.user if request else profile.user,
            request=request,
            action="UPDATE",
            description=(
                f"Manager assigned ({manager.email})"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Change Position
    # ============================================================

    @staticmethod
    @transaction.atomic
    def assign_position(
        *,
        profile,
        position,
        request=None,
    ):
        if position.company_id != profile.company_id:
            raise ValidationError(
                "Position does not belong to the employee's company."
            )

        profile.position = position

        profile.save(
            update_fields=[
                "position",
                "updated_at",
            ]
        )

        create_audit_log(
            user=request.user if request else profile.user,
            request=request,
            action="UPDATE",
            description=(
                f"Position changed to {position.title}"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Employee Transfer
    # ============================================================

    @staticmethod
    @transaction.atomic
    def transfer_employee(
        *,
        profile,
        new_branch,
        new_department,
        new_team,
        approved_by,
        reason,
        request=None,
    ):
        if not reason or not reason.strip():
            raise ValidationError(
                "Transfer reason is required."
            )

        if profile.company_id != new_branch.company_id:
            raise ValidationError(
                "New branch does not belong to the employee's company."
            )

        if new_department.company_id != profile.company_id:
            raise ValidationError(
                "New department does not belong to the employee's company."
            )

        if new_team.company_id != profile.company_id:
            raise ValidationError(
                "New team does not belong to the employee's company."
            )

        if new_department.branch_id != new_branch.id:
            raise ValidationError(
                "Department must belong to the new branch."
            )

        if new_team.branch_id != new_branch.id:
            raise ValidationError(
                "Team must belong to the new branch."
            )

        if new_team.department_id != new_department.id:
            raise ValidationError(
                "Team must belong to the selected department."
            )

        if approved_by.company_id != profile.company_id:
            raise ValidationError(
                "Approver does not belong to the employee's company."
            )

        EmployeeTransfer.objects.create(
            employee=profile,

            old_branch=profile.branch,
            new_branch=new_branch,

            old_department=profile.department,
            new_department=new_department,

            old_team=profile.team,
            new_team=new_team,

            approved_by=approved_by,
            reason=reason.strip(),
            effective_date=timezone.now().date(),
        )

        profile.branch = new_branch
        profile.department = new_department
        profile.team = new_team

        profile.save(
            update_fields=[
                "branch",
                "department",
                "team",
                "updated_at",
            ]
        )

        if hasattr(profile.user, "branch_id"):
            profile.user.branch = new_branch
            profile.user.save(
                update_fields=["branch"]
            )

        create_audit_log(
            user=approved_by,
            request=request,
            action="UPDATE",
            description=(
                f"Transferred employee "
                f"{profile.user.email}"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Suspend Employee
    # ============================================================

    @staticmethod
    @transaction.atomic
    def suspend_employee(
        *,
        profile,
        reason="",
        request=None,
    ):
        if profile.status == "TERMINATED":
            raise ValidationError(
                "A terminated employee cannot be suspended."
            )

        profile.status = "SUSPENDED"

        profile.user.is_active = False

        profile.user.save(
            update_fields=["is_active"]
        )

        profile.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            user=request.user,
            request=request,
            action="SECURITY",
            description=(
                f"Employee suspended. {reason}"
            ),
            obj=profile,
        )

        return profile

    # ============================================================
    # Activate Employee
    # ============================================================

    @staticmethod
    @transaction.atomic
    def activate_employee(
        *,
        profile,
        request=None,
    ):
        if profile.status == "TERMINATED":
            raise ValidationError(
                "A terminated employee cannot be activated."
            )

        profile.status = "ACTIVE"

        profile.user.is_active = True

        profile.user.save(
            update_fields=["is_active"]
        )

        profile.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            user=request.user,
            request=request,
            action="UPDATE",
            description="Employee activated.",
            obj=profile,
        )

        return profile

    # ============================================================
    # Terminate Employee
    # ============================================================

    @staticmethod
    @transaction.atomic
    def terminate_employee(
        *,
        profile,
        reason="",
        request=None,
    ):
        if profile.status == "TERMINATED":
            raise ValidationError(
                "Employee is already terminated."
            )

        profile.status = "TERMINATED"

        profile.user.is_active = False

        profile.user.save(
            update_fields=["is_active"]
        )

        profile.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        create_audit_log(
            user=request.user,
            request=request,
            action="DELETE",
            description=(
                f"Employment terminated. {reason}"
            ),
            obj=profile,
        )

        return profile