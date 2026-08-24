from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles
from security.viewsets import SecureModelViewSet
from core.audit import ActivityAudit

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer
from .permissions import IsSubscriptionAdmin
from .services import activate_subscription, cancel_subscription


class PlanViewSet(SecureModelViewSet):
    """
    System plans.
    Plans are system-level resources rather than company-owned resources.
    """

    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]
    audit_action = "PLAN"

    def get_queryset(self):
        user = self.request.user
        if user.role == Roles.SUPERUSER:
            return Plan.objects.all()
        return Plan.objects.filter(is_active=True)


class SubscriptionViewSet(SecureModelViewSet):
    """
    Manage the authenticated company's subscription.
    Only company administrators or system superusers may modify subscription state.
    """

    queryset = Subscription.objects.select_related("company", "plan")
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]
    audit_action = "SUBSCRIPTION"

    def get_queryset(self):
        user = self.request.user
        if user.role == Roles.SUPERUSER:
            return Subscription.objects.select_related("company", "plan")
        return Subscription.objects.select_related("company", "plan").filter(company=user.company)

    def perform_create(self, serializer):
        company = self.request.user.company
        plan = serializer.validated_data["plan"]

        activate_subscription(
            company=company,
            plan=plan,
            expires_at=serializer.validated_data.get("expires_at"),
            request=self.request,
            user=self.request.user,
        )

    def perform_update(self, serializer):
        subscription = self.get_object()
        old_plan = subscription.plan
        old_status = subscription.is_active

        plan = serializer.validated_data.get("plan", subscription.plan)
        expires_at = serializer.validated_data.get("expires_at", subscription.expires_at)

        subscription.plan = plan
        subscription.expires_at = expires_at

        if "is_active" in serializer.validated_data:
            subscription.is_active = serializer.validated_data["is_active"]

        subscription.save()

        ActivityAudit.log(
            user=self.request.user,
            company=subscription.company,
            action="SUBSCRIPTION_UPDATED",
            metadata={
                "subscription_id": str(subscription.id),
                "old_plan": old_plan.name,
                "new_plan": subscription.plan.name,
                "old_status": old_status,
                "new_status": subscription.is_active,
            },
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        subscription = self.get_object()

        cancel_subscription(subscription=subscription, request=request, user=request.user)

        ActivityAudit.log(
            user=request.user,
            company=subscription.company,
            action="SUBSCRIPTION_CANCELLED",
            metadata={
                "subscription_id": str(subscription.id),
                "plan": subscription.plan.name,
            },
        )

        return Response(
            {
                "message": "Subscription cancelled successfully.",
                "is_active": subscription.is_active,
                "is_valid": subscription.is_valid,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk=None):
        subscription = self.get_object()
        subscription.is_active = True
        subscription.save(update_fields=["is_active", "updated_at"])

        ActivityAudit.log(
            user=request.user,
            company=subscription.company,
            action="SUBSCRIPTION_REACTIVATED",
            metadata={
                "subscription_id": str(subscription.id),
                "plan": subscription.plan.name,
            },
        )

        return Response(
            {
                "message": "Subscription reactivated successfully.",
                "is_active": subscription.is_active,
                "is_valid": subscription.is_valid,
            },
            status=status.HTTP_200_OK,
        )
