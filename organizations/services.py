from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils import timezone

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles

from projects.models import ProjectMembership
from tasks.models import Task

from notifications.services import CommunicationService
from security.services import create_audit_log, terminate_user_sessions

from .models import (
    EmployeeDelegation,
    EmployeeProfile,
    EmployeeReplacement,
    EmployeeTransfer,
    Department,
    Team,
    Position,
    EmployeeCompensation,
    UserCapabilityGrant,
    PositionCapabilityGrant,
)


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
        terminate_user_sessions(
            profile.user,
            reason=f"Employee suspended: {reason}",
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
        terminate_user_sessions(
            profile.user,
            reason=f"Employee terminated: {reason}",
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


class EmployeeLifecycleService:

    @staticmethod
    @transaction.atomic
    def place_on_leave(
        *,
        profile,
        reason="",
        request=None,
    ):
        profile.status = "ON_LEAVE"
        profile.save(update_fields=["status"])

        create_audit_log(
            user=getattr(request, "user", None) if request else None,
            company=profile.company,
            branch=profile.branch,
            request=request,
            action="UPDATE",
            description=(
                f"Employee placed on leave: {profile.user.email}. "
                f"Reason: {reason}"
            ),
            obj=profile,
        )

        CommunicationService.send(
            recipient=profile.user,
            company=profile.company,
            notification_type="ORGANIZATION_UPDATE",
            title="Employment status updated",
            message="Your employment status has been changed to ON LEAVE.",
            send_email=True,
            email_subject="Employment status updated",
            email_template="emails/organization_update.html",
            email_context={
                "profile": profile,
                "message": reason,
            },
        )

        return profile

    @staticmethod
    @transaction.atomic
    def return_from_leave(
        *,
        profile,
        request=None,
    ):
        profile.status = "ACTIVE"
        profile.save(update_fields=["status"])

        create_audit_log(
            user=getattr(request, "user", None) if request else None,
            company=profile.company,
            branch=profile.branch,
            request=request,
            action="UPDATE",
            description=(
                f"Employee returned from leave: {profile.user.email}"
            ),
            obj=profile,
        )

        return profile

    @staticmethod
    @transaction.atomic
    def terminate(
        *,
        profile,
        reason,
        request=None,
    ):
        profile = EmployeeProfile.objects.select_for_update().select_related("user", "company").get(pk=profile.pk)
        if profile.status == "TERMINATED":
            raise ValidationError("Employee is already terminated.")
        if profile.user.role == Roles.ADMIN:
            from users.services import TenantUserLifecycleService
            TenantUserLifecycleService._guard_last_admin(profile.user, "terminate")
        if not reason.strip():
            raise ValidationError("A termination reason is required.")

        profile.status = "TERMINATED"
        profile.termination_date = timezone.localdate()
        profile.termination_reason = reason
        profile.terminated_by = getattr(request, "user", None) if request else None

        profile.save(
            update_fields=[
                "status",
                "termination_date",
                "termination_reason",
                "terminated_by",
            ]
        )

        user = profile.user
        user.is_active = False
        user.account_state = "TERMINATED"
        user.save(update_fields=["is_active", "account_state"])

        EmployeeDelegation.objects.filter(
            company=profile.company,
            status__in=["SCHEDULED", "ACTIVE"],
        ).filter(models.Q(from_user=user) | models.Q(to_user=user)).update(status="CANCELLED")
        terminate_user_sessions(user, reason=f"Employee terminated: {reason}")

        create_audit_log(
            user=getattr(request, "user", None) if request else None,
            company=profile.company,
            branch=profile.branch,
            request=request,
            action="DELETE",
            description=(
                f"Employment terminated for {user.email}. "
                f"Reason: {reason}"
            ),
            obj=profile,
        )

        return profile

    @staticmethod
    @transaction.atomic
    def require_password_reset(
        *,
        user,
        reason,
        request=None,
    ):
        user.must_change_password = True
        user.password_reset_required_at = timezone.now()
        user.save(
            update_fields=[
                "must_change_password",
                "password_reset_required_at",
            ]
        )

        from security.models import ActiveSession

        ActiveSession.objects.filter(
            user=user,
            is_active=True,
        ).update(
            is_active=False,
            terminated_at=timezone.now(),
        )

        create_audit_log(
            user=getattr(request, "user", None) if request else None,
            company=user.company,
            branch=user.branch,
            request=request,
            action="SECURITY",
            description=(
                f"Password reset required for {user.email}. "
                f"Reason: {reason}"
            ),
            obj=user,
        )

        CommunicationService.send(
            recipient=user,
            company=user.company,
            notification_type="SECURITY",
            title="Password reset required",
            message="Your account requires a password reset.",
            send_email=True,
            force_email=True,
            email_subject="Password reset required",
            email_template="emails/security_alert.html",
            email_context={
                "security_message": (
                    "A company administrator has required a password reset for your account."
                )
            },
        )

        return user


class DelegationService:

    ALLOWED_DELEGATION_PERMISSIONS = {
        "RECEIVE_REPORTS",
        "APPROVE_REPORTS",
        "APPROVE_REQUESTS",
        "MANAGE_TASKS",
        "REVIEW_SUBMISSIONS",
    }

    @staticmethod
    @transaction.atomic
    def create(
        *,
        from_user,
        to_user,
        permissions,
        starts_at,
        ends_at,
        reason="",
        created_by,
        request=None,
    ):
        permissions = set(permissions or [])

        if not permissions:
            raise ValidationError(
                "At least one delegation permission is required."
            )

        invalid = (
            permissions
            - DelegationService.ALLOWED_DELEGATION_PERMISSIONS
        )
        if invalid:
            raise ValidationError(
                "Invalid delegation permissions: "
                + ", ".join(sorted(invalid))
            )

        if from_user.company_id != to_user.company_id:
            raise ValidationError("Users belong to different companies.")

        if starts_at >= ends_at:
            raise ValidationError("Delegation end must be after start.")

        delegation = EmployeeDelegation.objects.create(
            company=from_user.company,
            from_user=from_user,
            to_user=to_user,
            permissions=sorted(permissions),
            starts_at=starts_at,
            ends_at=ends_at,
            reason=reason,
            created_by=created_by,
        )

        create_audit_log(
            user=created_by,
            company=from_user.company,
            branch=getattr(created_by, "branch", None),
            request=request,
            action="CREATE",
            description=(
                f"Delegation created from {from_user.email} to {to_user.email}."
            ),
            obj=delegation,
        )

        return delegation

    @staticmethod
    def active_for(
        *,
        user,
        permission=None,
    ):
        now = timezone.now()
        queryset = EmployeeDelegation.objects.filter(
            to_user=user,
            starts_at__lte=now,
            ends_at__gte=now,
            status__in=["SCHEDULED", "ACTIVE"],
        )

        if permission:
            return any(
                permission in delegation.permissions
                for delegation in queryset
            )

        return queryset.exists()


class EmployeeReplacementService:

    @staticmethod
    @transaction.atomic
    def execute(
        *,
        outgoing,
        incoming,
        transfer_open_tasks=True,
        transfer_project_memberships=True,
        transfer_team_leadership=False,
        transfer_department_management=False,
        transfer_branch_management=False,
        reason="",
        performed_by,
        request=None,
    ):
        if outgoing.company_id != incoming.company_id:
            raise ValidationError("Employees belong to different companies.")

        if outgoing.id == incoming.id:
            raise ValidationError("Employee cannot replace themselves.")

        replacement = EmployeeReplacement.objects.create(
            company=outgoing.company,
            outgoing_employee=outgoing,
            incoming_employee=incoming,
            transfer_open_tasks=transfer_open_tasks,
            transfer_project_memberships=transfer_project_memberships,
            transfer_team_leadership=transfer_team_leadership,
            transfer_department_management=transfer_department_management,
            transfer_branch_management=transfer_branch_management,
            reason=reason,
            performed_by=performed_by,
        )

        old_user = outgoing.user
        new_user = incoming.user

        if transfer_open_tasks:
            tasks = (
                Task.objects.filter(
                    company=outgoing.company,
                    assignees=old_user,
                    is_active=True,
                )
                .exclude(status="done")
            )

            for task in tasks:
                task.assignees.remove(old_user)
                task.assignees.add(new_user)

        if transfer_project_memberships:
            memberships = ProjectMembership.objects.filter(
                user=old_user,
                project__company=outgoing.company,
            )

            for membership in memberships:
                ProjectMembership.objects.get_or_create(
                    project=membership.project,
                    user=new_user,
                    defaults={
                        "role": membership.role,
                        "added_by": performed_by,
                    },
                )

        if transfer_team_leadership:
            from .models import Team

            Team.objects.filter(
                company=outgoing.company,
                leader=old_user,
            ).update(leader=new_user)

        if transfer_department_management:
            from .models import Department

            Department.objects.filter(
                company=outgoing.company,
                manager=old_user,
            ).update(manager=new_user)

        if transfer_branch_management:
            from companies.models import Branch

            Branch.objects.filter(
                company=outgoing.company,
                manager=old_user,
            ).update(manager=new_user)

        replacement.status = "COMPLETED"
        replacement.completed_at = timezone.now()
        replacement.save(update_fields=["status", "completed_at"])

        create_audit_log(
            user=performed_by,
            company=outgoing.company,
            branch=getattr(performed_by, "branch", None),
            request=request,
            action="UPDATE",
            description=(
                f"Responsibilities transferred from {old_user.email} "
                f"to {new_user.email}."
            ),
            obj=replacement,
        )

        return replacement


class CompensationService:

    @staticmethod
    @transaction.atomic
    def set_compensation(
        *,
        employee,
        base_salary,
        currency,
        effective_from,
        housing_allowance=0,
        transport_allowance=0,
        other_allowance=0,
        notes="",
        user,
        request=None,
    ):
        if not CapabilityService.has(
            user,
            Capabilities.MANAGE_COMPENSATION,
        ):
            raise ValidationError(
                "You do not have permission to manage compensation."
            )

        if (
            employee.company_id != user.company_id
        ):
            raise ValidationError("Employee belongs to another company.")

        current = EmployeeCompensation.objects.filter(
            employee=employee,
            company=employee.company,
            is_current=True,
        ).first()

        if current:
            from datetime import timedelta

            current.is_current = False
            current.effective_to = effective_from - timedelta(days=1)
            current.save(
                update_fields=[
                    "is_current",
                    "effective_to",
                    "updated_at",
                ]
            )

        compensation = EmployeeCompensation.objects.create(
            employee=employee,
            company=employee.company,
            base_salary=base_salary,
            currency=currency,
            housing_allowance=housing_allowance,
            transport_allowance=transport_allowance,
            other_allowance=other_allowance,
            effective_from=effective_from,
            notes=notes,
            is_current=True,
            created_by=user,
        )

        create_audit_log(
            user=user,
            company=employee.company,
            branch=employee.branch,
            request=request,
            action="UPDATE",
            description="Employee compensation record updated.",
            obj=compensation,
        )

        return compensation


class CapabilityGrantService:

    SENSITIVE_CAPABILITIES = {
        Capabilities.VIEW_COMPENSATION,
        Capabilities.MANAGE_COMPENSATION,
        Capabilities.VIEW_COMPENSATION_HISTORY,
        Capabilities.MANAGE_COMPENSATION_ACCESS,
        Capabilities.VIEW_FINANCIAL_REPORTS,
    }

    @staticmethod
    def can_manage_sensitive_access(*, actor, company):
        # Platform identities never manage tenant-sensitive access implicitly.
        if actor.role == Roles.SUPERUSER or getattr(actor, "is_superuser", False):
            return False

        if actor.company_id != company.id:
            return False

        if company.created_by_id == actor.id:
            return True

        return CapabilityService.has(
            actor,
            Capabilities.MANAGE_COMPENSATION_ACCESS,
        )

    @classmethod
    @transaction.atomic
    def grant_user(
        cls,
        *,
        company,
        target_user,
        capability,
        actor,
        reason="",
        request=None,
    ):
        if target_user.company_id != company.id:
            raise ValidationError("User belongs to another company.")

        if (
            not Capabilities.is_assignable_by_company_admin(capability)
        ):
            raise ValidationError(
                "This capability is reserved for platform administration."
            )

        if (
            capability in cls.SENSITIVE_CAPABILITIES
            and not cls.can_manage_sensitive_access(
                actor=actor,
                company=company,
            )
        ):
            raise ValidationError(
                "You cannot grant this sensitive capability."
            )

        grant, created = UserCapabilityGrant.objects.get_or_create(
            company=company,
            user=target_user,
            capability=capability,
            defaults={
                "granted_by": actor,
                "reason": reason,
                "is_active": True,
            },
        )

        if not created:
            grant.is_active = True
            grant.revoked_at = None
            grant.revoked_by = None
            grant.granted_by = actor
            grant.reason = reason
            grant.save(
                update_fields=[
                    "is_active",
                    "revoked_at",
                    "revoked_by",
                    "granted_by",
                    "reason",
                ]
            )

        create_audit_log(
            user=actor,
            company=company,
            request=request,
            action="SECURITY",
            description=(
                f"Capability {capability} granted to {target_user.email}."
            ),
            obj=grant,
        )

        return grant

    @staticmethod
    @transaction.atomic
    def revoke_user(*, grant, actor, reason="", request=None):
        grant.is_active = False
        grant.revoked_at = timezone.now()
        grant.revoked_by = actor

        if reason:
            grant.reason = reason

        grant.save(
            update_fields=[
                "is_active",
                "revoked_at",
                "revoked_by",
                "reason",
            ]
        )

        create_audit_log(
            user=actor,
            company=grant.company,
            request=request,
            action="SECURITY",
            description=(
                f"Capability {grant.capability} revoked from "
                f"{grant.user.email}."
            ),
            obj=grant,
        )

        return grant

    @classmethod
    @transaction.atomic
    def grant_position(
        cls,
        *,
        company,
        position,
        capability,
        actor,
        reason="",
        request=None,
    ):
        if position.company_id != company.id:
            raise ValidationError("Position belongs to another company.")

        if (
            not Capabilities.is_assignable_by_company_admin(capability)
        ):
            raise ValidationError(
                "This capability is reserved for platform administration."
            )

        grant, _ = PositionCapabilityGrant.objects.get_or_create(
            company=company,
            position=position,
            capability=capability,
            defaults={
                "granted_by": actor,
                "reason": reason,
                "is_active": True,
            },
        )
        if not grant.is_active:
            grant.is_active = True
            grant.granted_by = actor
            grant.reason = reason
            grant.save(update_fields=["is_active", "granted_by", "reason"])

        create_audit_log(
            user=actor,
            company=company,
            request=request,
            action="SECURITY",
            description=(
                f"Capability {capability} granted to position {position.title}."
            ),
            obj=grant,
        )
        return grant