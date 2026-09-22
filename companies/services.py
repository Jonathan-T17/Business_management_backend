from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles
from security.services import create_audit_log, terminate_company_sessions, terminate_user_sessions
from subscriptions.services import SubscriptionService
from users.utils import send_invitation_email
from .models import Branch, Company, CompanyInvite


class CompanyInviteService:
    DEFAULT_EXPIRATION_DAYS = 3
    ALLOWED_TENANT_ROLES = {Roles.ADMIN, Roles.MANAGER, Roles.EMPLOYEE}

    @classmethod
    @transaction.atomic
    def create_invite(cls, *, company, email, role, created_by, request=None, days_valid=None, position=None):
        if created_by.company_id != company.id or created_by.role == Roles.SUPERUSER:
            raise PermissionDenied("Tenant invitations require a company administrator context.")
        if not CapabilityService.has(created_by, Capabilities.MANAGE_EMPLOYEES):
            raise PermissionDenied("You do not have permission to manage employees.")
        if role not in cls.ALLOWED_TENANT_ROLES:
            raise ValidationError("Only tenant roles may be invited.")
        if role == Roles.ADMIN and created_by.role != Roles.ADMIN:
            raise PermissionDenied("Only a Company Administrator may invite another Company Administrator.")
        if not company.is_active:
            raise ValidationError("Cannot invite users to an inactive company.")
        if not SubscriptionService.can_add_user(company):
            raise ValidationError("Your subscription user limit has been reached.")

        if position:
            if position.company_id != company.pk or not position.is_active:
                raise ValidationError("Choose an active position in your company.")
            from company_setup.capability_policy import SetupCapabilityPolicy
            SetupCapabilityPolicy.validate_preset(actor=created_by, capabilities=list(position.capability_grants.filter(is_active=True).values_list("capability",flat=True)))
        email = email.lower().strip()
        from users.models import User
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user:
            raise ValidationError("This email already belongs to an existing SmartBiz account.")

        existing = CompanyInvite.objects.select_for_update().filter(
            company=company, email__iexact=email, status="PENDING"
        ).first()
        if existing and existing.expires_at > timezone.now():
            raise ValidationError("A pending invitation already exists for this email.")
        if existing:
            existing.status = "EXPIRED"
            existing.save(update_fields=["status"])

        duration = days_valid if isinstance(days_valid, int) and 1 <= days_valid <= 7 else cls.DEFAULT_EXPIRATION_DAYS
        try:
            invite = CompanyInvite.objects.create(
                company=company, email=email, role=role, created_by=created_by, position=position,
                expires_at=timezone.now() + timedelta(days=duration),
            )
        except IntegrityError:
            raise ValidationError("A pending invitation already exists for this email.")

        transaction.on_commit(lambda: send_invitation_email(
            CompanyInvite.objects.select_related("company", "created_by").get(pk=invite.pk)
        ))
        create_audit_log(user=created_by, company=company, request=request, action="INVITE_CREATED",
                         description=f"Company invitation created for {email} with role {role}.", obj=invite)
        return invite

    @classmethod
    @transaction.atomic
    def accept_invite(cls, *, invite, user, request=None):
        invite = CompanyInvite.objects.select_for_update().select_related("company").get(pk=invite.pk)
        if invite.status != "PENDING":
            raise ValidationError("This invitation is no longer pending.")
        if invite.expires_at <= timezone.now():
            invite.status = "EXPIRED"; invite.save(update_fields=["status"])
            raise ValidationError("This invitation has expired.")
        if not invite.company.is_active:
            raise ValidationError("This company is currently inactive.")
        if invite.role not in cls.ALLOWED_TENANT_ROLES:
            raise ValidationError("This invitation contains an invalid tenant role.")
        if user.role == Roles.SUPERUSER or user.is_superuser:
            raise PermissionDenied("Platform accounts cannot join tenant companies.")
        if user.email.lower() != invite.email.lower():
            raise PermissionDenied("This invitation was issued to a different email address.")
        if user.company_id and user.company_id != invite.company_id:
            raise ValidationError("You already belong to another company.")
        from subscriptions.services import SubscriptionCapacity
        type(invite.company).objects.select_for_update().get(pk=invite.company_id)
        subscription = SubscriptionService.require_active(invite.company)
        if SubscriptionCapacity.usage(invite.company)["users"] > subscription.plan.max_users:
            raise ValidationError("The subscription user limit has been reached.")

        position = invite.position
        if position and (position.company_id != invite.company_id or not position.is_active):
            raise ValidationError("The invitation position is no longer available. Ask your administrator to send a new invitation.")
        user.company = invite.company
        user.role = invite.role
        user.is_staff = False
        user.save(update_fields=["company", "role", "is_staff"])
        from organizations.models import EmployeeProfile
        if position:
            user.branch = position.branch
            user.save(update_fields=["branch"])
            EmployeeProfile.objects.update_or_create(user=user, defaults={
                "company":invite.company, "employee_id":f"INV-{invite.pk}",
                "position":position,"branch":position.branch,"department":position.department,
                "team":position.team,
            })
        else:
            EmployeeProfile.objects.get_or_create(user=user, defaults={
                "company":invite.company, "employee_id":f"INV-{invite.pk}",
            })
        invite.status = "ACCEPTED"
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])
        create_audit_log(user=user, company=invite.company, request=request, action="INVITE_ACCEPTED",
                         description="Company invitation accepted.", obj=invite)
        return invite

    @staticmethod
    @transaction.atomic
    def revoke_invite(*, invite, user, request=None):
        invite = CompanyInvite.objects.select_for_update().get(pk=invite.pk)
        if invite.company_id != user.company_id:
            raise PermissionDenied("Invitation belongs to another company.")
        if invite.status != "PENDING":
            raise ValidationError("Only pending invitations can be revoked.")
        invite.status = "REVOKED"
        invite.save(update_fields=["status"])
        create_audit_log(user=user, company=invite.company, request=request, action="INVITE_REVOKED",
                         description=f"Invitation revoked for {invite.email}.", obj=invite)
        return invite


class CompanyLifecycleService:
    @staticmethod
    @transaction.atomic
    def deactivate(*, company, actor, reason, request=None):
        company = Company.objects.select_for_update().get(pk=company.pk)
        if actor.role != Roles.SUPERUSER:
            raise PermissionDenied("Company suspension/deactivation is a platform operation.")
        if not reason.strip():
            raise ValidationError("A reason is required.")
        company.is_active = False
        company.save(update_fields=["is_active"])
        terminate_company_sessions(company, reason=reason)
        create_audit_log(user=actor, company=company, request=request, action="COMPANY_DEACTIVATED",
                         description=f"Company deactivated. Reason: {reason}", obj=company)
        return company

    @staticmethod
    @transaction.atomic
    def reactivate(*, company, actor, reason, request=None):
        company = Company.objects.select_for_update().get(pk=company.pk)
        if actor.role != Roles.SUPERUSER:
            raise PermissionDenied("Company reactivation is a platform operation.")
        if not reason.strip():
            raise ValidationError("A reason is required.")
        company.is_active = True
        company.save(update_fields=["is_active"])
        create_audit_log(user=actor, company=company, request=request, action="COMPANY_REACTIVATED",
                         description=f"Company reactivated. Reason: {reason}", obj=company)
        return company


class BranchLifecycleService:
    @staticmethod
    @transaction.atomic
    def deactivate(*, branch, actor, reason, request=None):
        branch = Branch.objects.select_for_update().get(pk=branch.pk)
        if actor.company_id != branch.company_id or not CapabilityService.has(actor, Capabilities.MANAGE_ORGANIZATION):
            raise PermissionDenied("You cannot manage this branch.")
        if not reason.strip():
            raise ValidationError("A reason is required.")
        blockers = []
        active_users = branch.users.filter(is_active=True, is_deleted=False).count()
        if active_users:
            blockers.append(f"{active_users} active user(s) are still assigned to this branch")
        if blockers:
            raise ValidationError({"blockers": blockers})
        branch.is_active = False
        branch.save(update_fields=["is_active"])
        create_audit_log(user=actor, company=branch.company, branch=branch, request=request,
                         action="BRANCH_DEACTIVATED", description=f"Branch deactivated. Reason: {reason}", obj=branch)
        return branch

    @staticmethod
    @transaction.atomic
    def activate(*, branch, actor, reason="", request=None):
        branch = Branch.objects.select_for_update().get(pk=branch.pk)
        if actor.company_id != branch.company_id or not CapabilityService.has(actor, Capabilities.MANAGE_ORGANIZATION):
            raise PermissionDenied("You cannot manage this branch.")
        if not branch.company.is_active:
            raise ValidationError("Cannot activate a branch while the company is inactive.")
        branch.is_active = True
        branch.save(update_fields=["is_active"])
        create_audit_log(user=actor, company=branch.company, branch=branch, request=request,
                         action="BRANCH_ACTIVATED", description=f"Branch activated. Reason: {reason}", obj=branch)
        return branch
