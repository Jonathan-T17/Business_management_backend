from django.db import transaction

from security.services import create_audit_log

from .models import Subscription


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

        current_users = company.users.filter(
            is_deleted=False
        ).count()

        return (
            current_users
            < subscription.plan.max_users
        )


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