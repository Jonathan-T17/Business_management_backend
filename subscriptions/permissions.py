from django.utils import timezone
from rest_framework.permissions import BasePermission

from core.roles import Roles


class IsSubscriptionAdmin(BasePermission):
    """
    Only company administrators and the system superuser
    can manage subscriptions.
    """

    message = "You do not have permission to manage subscriptions."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.user.role == Roles.SUPERUSER:
            return True

        return request.user.role == Roles.ADMIN




class HasActiveSubscription(BasePermission):
    message = "Your company does not have an active subscription."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        company = getattr(user, "company", None)

        if not company:
            return False

        subscription = getattr(
            company,
            "subscription",
            None,
        )

        if not subscription:
            return False

        if not subscription.is_active:
            return False

        if (
            subscription.expires_at
            and subscription.expires_at <= timezone.now()
        ):
            return False

        return True


class HasAIAnalyticsAccess(BasePermission):
    message = "AI analytics is not enabled for your subscription."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        company = getattr(user, "company", None)

        if not company:
            return False

        subscription = getattr(
            company,
            "subscription",
            None,
        )

        if not subscription:
            return False

        if not subscription.is_active:
            return False

        if (
            subscription.expires_at
            and subscription.expires_at <= timezone.now()
        ):
            return False

        return bool(
            subscription.plan.ai_analytics_enabled
        )