from django.db import transaction

from security.services import create_audit_log

from .models import Subscription


from rest_framework.exceptions import PermissionDenied,ValidationError
from core.capability_service import CapabilityService
from core.capabilities import Capabilities


@transaction.atomic
def activate_subscription(
    *,
    company,
    plan,
    request=None,
    user=None,
    expires_at=None,
):
    """
    Create or replace the company's subscription.
    """

    subscription, created = Subscription.objects.update_or_create(
        company=company,
        defaults={
            "plan": plan,
            "is_active": True,
            "expires_at": expires_at,
        },
    )

    action = (
        "SUBSCRIPTION_CREATED"
        if created
        else "SUBSCRIPTION_UPDATED"
    )

    create_audit_log(
        user=user,
        action=action,
        request=request,
        description=(
            f"Subscription "
            f"{'created' if created else 'updated'} "
            f"for {company.name}: {plan.name}"
        ),
        status="SUCCESS",
    )

    return subscription


@transaction.atomic
def cancel_subscription(
    *,
    subscription,
    request=None,
    user=None,
):
    """
    Deactivate a subscription without deleting its history.
    """

    subscription.is_active = False
    subscription.save(
        update_fields=[
            "is_active",
            "updated_at",
        ]
    )

    create_audit_log(
        user=user,
        action="SUBSCRIPTION_CANCELLED",
        request=request,
        description=(
            f"Subscription cancelled for "
            f"{subscription.company.name}"
        ),
        status="SUCCESS",
    )

    return subscription


from django.utils import timezone
from rest_framework.exceptions import PermissionDenied


class SubscriptionService:

    @staticmethod
    def get_active(company):

        try:
            subscription = company.subscription
        except Exception:
            return None

        if not subscription.is_active:
            return None

        if (
            subscription.expires_at
            and subscription.expires_at
            <= timezone.now()
        ):
            return None

        return subscription


    @classmethod
    def require_active(cls, company):

        subscription = cls.get_active(
            company
        )

        if not subscription:
            raise PermissionDenied(
                "An active subscription is required."
            )

        return subscription


    @classmethod
    def can_add_user(cls, company):

        subscription = cls.require_active(
            company
        )

        return SubscriptionCapacity.usage(company)["users"] < subscription.plan.max_users



    @classmethod
    def can_add_project(cls, company):

        subscription = cls.require_active(
            company
        )

        current_projects = company.projects.filter(
            is_active=True
        ).count()

        return (
            current_projects
            < subscription.plan.max_projects
        )

    @classmethod
    def can_add_branch(cls, company):
        subscription = cls.require_active(company)
        return company.branches.filter(is_active=True).count() < subscription.plan.max_branches

    @classmethod
    def storage_used_bytes(cls, company):
        from django.db.models import Sum
        from documents.models import Attachment

        return Attachment.objects.filter(
            company=company,
            is_active=True,
        ).aggregate(total=Sum("file_size"))["total"] or 0

    @classmethod
    def can_upload(cls, company, additional_bytes=0):
        subscription = cls.require_active(company)
        return (
            cls.storage_used_bytes(company) + additional_bytes
            <= subscription.plan.storage_limit_bytes
        )

    @classmethod
    def has_feature(cls, company, feature):
        subscription = cls.require_active(company)
        feature_map = {
            "ADVANCED_ANALYTICS": subscription.plan.ai_analytics_enabled,
            "REPORTING": subscription.plan.reports_enabled,
            "FIELD_OPERATIONS": subscription.plan.field_operations_enabled,
            "ADVANCED_WORKFLOWS": subscription.plan.advanced_workflows_enabled,
            "OFFICIAL_RECORDS": subscription.plan.official_records_enabled,
            "CUSTOM_FORMS": subscription.plan.custom_forms_enabled,
        }
        return feature_map.get(feature, False)

    @classmethod
    def usage(cls, company):
        subscription = cls.require_active(company)
        return {
            "users": {
                "used": company.users.filter(is_deleted=False).count(),
                "limit": subscription.plan.max_users,
            },
            "projects": {
                "used": company.projects.filter(is_active=True).count(),
                "limit": subscription.plan.max_projects,
            },
            "branches": {
                "used": company.branches.filter(is_active=True).count(),
                "limit": subscription.plan.max_branches,
            },
            "storage": {
                "used_bytes": cls.storage_used_bytes(company),
                "limit_bytes": subscription.plan.storage_limit_bytes,
            },
        }


    @classmethod
    def reports_enabled(cls, company):

        subscription = cls.require_active(
            company
        )

        return (
            subscription.plan.reports_enabled
        )


    @classmethod
    def ai_enabled(cls, company):

        subscription = cls.require_active(
            company
        )

        return (
            subscription.plan.ai_analytics_enabled
        )




class SubscriptionCapacity:
    @staticmethod
    def usage(company):
        return {
            "users": company.users.filter(is_deleted=False).count() + company.invites.filter(status="PENDING").exclude(email__in=company.users.filter(is_deleted=False).values("email")).count(),
            "projects": company.projects.filter(is_active=True).count(),
            "branches": company.branches.filter(is_active=True).count(),
        }

    @classmethod
    def issues(cls, company, plan):
        usage = cls.usage(company)
        messages = []
        for name in ("users", "projects", "branches"):
            limit = getattr(plan, "max_" + name)
            if usage[name] > limit:
                label = "user seats (including pending invitations)" if name == "users" else "active " + name
                messages.append(f"This plan allows {limit} {name}; the company currently uses {usage[name]} {label}.")
        return messages

    @classmethod
    def validate(cls, company, plan):
        issues = cls.issues(company, plan)
        if issues:
            raise ValidationError({"plan": issues})


class SubscriptionLifecycleService:
    @classmethod
    @transaction.atomic
    def change_plan(cls,*,subscription,new_plan,actor,reason,request=None):
        if not CapabilityService.has(actor,Capabilities.MANAGE_PLATFORM_SUBSCRIPTIONS):raise PermissionDenied("Platform subscription authority is required.")
        reason=(reason or "").strip()
        if not reason:raise ValidationError("A reason is required.")
        locked=type(subscription).objects.select_for_update().get(pk=subscription.pk)
        if not new_plan.is_active:
            raise ValidationError({"plan": "Choose an active plan."})
        if locked.plan_id == new_plan.pk:
            raise ValidationError({"plan": "This subscription already uses this plan."})
        SubscriptionCapacity.validate(locked.company, new_plan)
        old=locked.plan
        locked.plan=new_plan
        locked.save(update_fields=["plan","updated_at"])
        create_audit_log(user=actor,company=locked.company,request=request,action="UPDATE",description=f"Subscription plan changed from {old.name} to {new_plan.name}.",obj=locked,metadata={"reason":reason,"old_plan_id":old.pk,"new_plan_id":new_plan.pk})
        return locked
    @classmethod
    @transaction.atomic
    def reactivate(cls,*,subscription,actor,reason,request=None):
        if not CapabilityService.has(actor,Capabilities.MANAGE_PLATFORM_SUBSCRIPTIONS):raise PermissionDenied("Platform subscription authority is required.")
        reason=(reason or "").strip()
        if not reason:raise ValidationError("A reason is required.")
        locked=type(subscription).objects.select_for_update().get(pk=subscription.pk);locked.is_active=True;locked.save(update_fields=["is_active","updated_at"])
        create_audit_log(user=actor,company=locked.company,request=request,action="UPDATE",description="Subscription reactivated.",obj=locked,metadata={"reason":reason});return locked


class TenantSubscriptionService:
    @staticmethod
    @transaction.atomic
    def cancel(*, subscription, actor, reason, request=None):
        if (CapabilityService.is_platform_identity(actor) or actor.role != "ADMIN"
                or actor.company_id != subscription.company_id):
            raise PermissionDenied("Company administrator access is required.")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise ValidationError({"reason": "Provide a reason of up to 1,000 characters."})
        locked = Subscription.objects.select_for_update().get(pk=subscription.pk)
        if not locked.is_active:
            raise ValidationError("This subscription is already cancelled.")
        locked.is_active = False
        locked.save(update_fields=["is_active", "updated_at"])
        create_audit_log(user=actor, company=locked.company, request=request, action="SUBSCRIPTION_CANCELLED",
            obj=locked, description="Company subscription cancelled.", metadata={"reason": reason.strip()})
        return locked
