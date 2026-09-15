from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles
from security.services import create_audit_log, terminate_user_sessions
from subscriptions.models import Plan, Subscription
from subscriptions.services import SubscriptionService
from companies.models import Company
from .models import User


class UserService:
    @staticmethod
    @transaction.atomic
    def register_invited_user(*, email, full_name, password, invite_token):
        from companies.models import CompanyInvite
        from companies.services import CompanyInviteService

        try:
            invite = (CompanyInvite.objects.select_for_update()
                      .select_related("company")
                      .get(token=invite_token))
        except CompanyInvite.DoesNotExist:
            raise ValidationError({"invite": "Invitation not found or no longer valid."})

        if not invite.is_valid:
            raise ValidationError({"invite": "Invitation is expired or no longer valid."})
        if email.lower().strip() != invite.email.lower():
            raise ValidationError({"email": "This email does not match the invitation."})
        existing = User.objects.select_for_update().filter(email__iexact=email).first()
        if existing:
            from data_tools.models import ImportJob
            imported = ImportJob.objects.filter(company=invite.company, status="COMPLETED",
                import_type="EMPLOYEES", validation_result__valid_rows__contains=[{"email":email.strip().lower()}]).exists()
            if (not imported or existing.company_id != invite.company_id or existing.is_active
                    or existing.email_verified or existing.is_deleted or existing.is_superuser
                    or existing.is_staff or existing.role != Roles.EMPLOYEE or existing.has_usable_password()
                    or existing.account_state != "PENDING_VERIFICATION"):
                raise ValidationError({"email": "A user with this email already exists."})
        if invite.role == Roles.SUPERUSER:
            raise ValidationError({"invite": "Platform roles cannot be assigned through tenant invitations."})

        if existing:
            from django.contrib.auth.password_validation import validate_password
            validate_password(password, user=existing)
            user = existing
            user.set_password(password)
            user.save(update_fields=["password"])
        else:
            user = User.objects.create_user(
                email=email.lower().strip(), full_name=full_name, password=password,
                company=invite.company, role=invite.role, is_active=False,
                email_verified=False, account_state="PENDING_VERIFICATION",
            )
        CompanyInviteService.accept_invite(invite=invite, user=user)
        return user

    @staticmethod
    @transaction.atomic
    def register_company_admin(*, email, full_name, password, company_name):
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": "A user with this email already exists."})
        try:
            company = Company.objects.create(name=company_name.strip())
        except IntegrityError:
            raise ValidationError({"company_name": "This company name is already registered."})

        user = User.objects.create_user(
            email=email.lower().strip(), full_name=full_name, password=password,
            company=company, role=Roles.ADMIN, is_active=False,
            email_verified=False, account_state="PENDING_VERIFICATION",
        )
        company.created_by = user
        company.save(update_fields=["created_by"])

        default_plan_name = getattr(settings, "SMARTBIZ_DEFAULT_SIGNUP_PLAN_NAME", "Starter")
        plan = Plan.objects.filter(name=default_plan_name, is_active=True).first()
        if not plan:
            raise ValidationError({"plan": "Default signup plan is not configured."})
        Subscription.objects.create(company=company, plan=plan, is_active=True)

        try:
            from company_setup.models import CompanySetupState
            CompanySetupState.objects.get_or_create(company=company)
        except Exception:
            # Company registration must not depend on optional setup migrations
            # being imported during historical migration execution.
            pass

        create_audit_log(user=user, company=company, action="COMPANY_REGISTERED",
                         description="Company registration created.")
        return user


class TenantUserLifecycleService:
    TENANT_ROLES = {Roles.ADMIN, Roles.MANAGER, Roles.EMPLOYEE}

    @staticmethod
    def _require_actor(actor, company):
        if not actor or not actor.is_authenticated or actor.company_id != company.id:
            raise ValidationError("A tenant administrator from the same company is required.")
        if not CapabilityService.has(actor, Capabilities.MANAGE_EMPLOYEES):
            raise ValidationError("You do not have permission to manage employees.")

    @staticmethod
    def _is_last_active_admin(user):
        if user.role != Roles.ADMIN or not user.company_id:
            return False
        return not User.objects.filter(
            company_id=user.company_id, role=Roles.ADMIN, is_active=True,
            is_deleted=False, account_state="ACTIVE",
        ).exclude(pk=user.pk).exists()

    @classmethod
    def _guard_last_admin(cls, user, action):
        if cls._is_last_active_admin(user):
            raise ValidationError(f"Cannot {action} the last active company administrator.")

    @classmethod
    @transaction.atomic
    def change_role(cls, *, actor, target, new_role, reason="", request=None):
        target = User.objects.select_for_update().get(pk=target.pk)
        cls._require_actor(actor, target.company)
        if target.role == Roles.SUPERUSER or target.is_superuser:
            raise ValidationError("Platform accounts cannot be managed through tenant endpoints.")
        if new_role not in cls.TENANT_ROLES:
            raise ValidationError("Only tenant roles can be assigned here.")
        if new_role == Roles.ADMIN and actor.role != Roles.ADMIN:
            raise ValidationError("Only a Company Administrator may promote another Company Administrator.")
        if target.role == Roles.ADMIN and new_role != Roles.ADMIN:
            cls._guard_last_admin(target, "demote")
        old_role = target.role
        target.role = new_role
        target.is_staff = False
        target.save(update_fields=["role", "is_staff"])
        create_audit_log(user=actor, company=target.company, branch=target.branch, request=request,
                         action="USER_ROLE_CHANGED", obj=target,
                         description=f"Tenant role changed from {old_role} to {new_role}. Reason: {reason}")
        return target

    @classmethod
    @transaction.atomic
    def deactivate(cls, *, actor, target, reason, request=None):
        target = User.objects.select_for_update().get(pk=target.pk)
        cls._require_actor(actor, target.company)
        if not reason.strip():
            raise ValidationError("A deactivation reason is required.")
        if target.role == Roles.SUPERUSER or target.is_superuser:
            raise ValidationError("Platform accounts cannot be managed through tenant endpoints.")
        if target.role == Roles.ADMIN:
            cls._guard_last_admin(target, "deactivate")
        target.is_active = False
        target.account_state = "DEACTIVATED"
        target.save(update_fields=["is_active", "account_state"])
        terminate_user_sessions(target, reason=reason)
        create_audit_log(user=actor, company=target.company, branch=target.branch, request=request,
                         action="USER_DEACTIVATED", obj=target,
                         description=f"User deactivated. Reason: {reason}")
        return target

    @classmethod
    @transaction.atomic
    def reactivate(cls, *, actor, target, reason, request=None):
        target = User.objects.select_for_update().get(pk=target.pk)
        cls._require_actor(actor, target.company)
        if not reason.strip():
            raise ValidationError("A reactivation reason is required.")
        if target.is_deleted or target.account_state == "TERMINATED":
            raise ValidationError("Terminated or deleted accounts cannot be reactivated through this action.")
        if not target.email_verified:
            raise ValidationError("Email verification is required before activation.")
        if not target.company or not target.company.is_active:
            raise ValidationError("The company is inactive.")
        profile = getattr(target, "employee_profile", None)
        if profile and profile.status in {"SUSPENDED", "TERMINATED"}:
            raise ValidationError("Resolve the employee lifecycle status before reactivation.")
        if not SubscriptionService.can_add_user(target.company):
            raise ValidationError("The subscription user limit has been reached.")
        target.is_active = True
        target.account_state = "ACTIVE"
        target.save(update_fields=["is_active", "account_state"])
        create_audit_log(user=actor, company=target.company, branch=target.branch, request=request,
                         action="USER_REACTIVATED", obj=target,
                         description=f"User reactivated. Reason: {reason}")
        return target

    @staticmethod
    @transaction.atomic
    def verify_email(*, user, request=None):
        user = User.objects.select_for_update().get(pk=user.pk)
        user.email_verified = True
        fields = ["email_verified"]
        # Verification may activate only an account still awaiting verification.
        # It never overrides a suspension/deactivation/termination.
        if user.account_state == "PENDING_VERIFICATION" and user.company and user.company.is_active:
            user.account_state = "ACTIVE"
            user.is_active = True
            fields += ["account_state", "is_active"]
        user.save(update_fields=fields)
        create_audit_log(user=user, company=user.company, branch=user.branch, request=request,
                         action="EMAIL_VERIFIED", obj=user, description="Email verified.")
        return user

    @staticmethod
    @transaction.atomic
    def password_reset_completed(*, user, new_password, request=None):
        user = User.objects.select_for_update().get(pk=user.pk)
        user.set_password(new_password)
        user.must_change_password = False
        user.password_reset_required_at = None
        user.save(update_fields=["password", "must_change_password", "password_reset_required_at"])
        terminate_user_sessions(user, reason="Password reset completed")
        create_audit_log(user=user, company=user.company, branch=user.branch, request=request,
                         action="PASSWORD_RESET_COMPLETED", obj=user, description="Password reset completed.")
        return user
