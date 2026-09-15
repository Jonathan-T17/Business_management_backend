from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer
from .permissions import IsSubscriptionAdmin
from .services import SubscriptionService


class PlanViewSet(ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]

    def get_queryset(self):
        return Plan.objects.filter(is_active=True)


class SubscriptionViewSet(ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]

    def get_queryset(self):
        return Subscription.objects.select_related("company", "plan").filter(company=self.request.user.company)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        from .services import TenantSubscriptionService
        subscription = TenantSubscriptionService.cancel(subscription=self.get_object(), actor=request.user,
            reason=request.data.get("reason", ""), request=request)
        return Response(self.get_serializer(subscription).data)


class SubscriptionUsageView(APIView):
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]

    def get(self, request):
        return Response(SubscriptionService.usage(request.user.company))


class SubscriptionFeaturesView(APIView):
    permission_classes = [IsAuthenticated, IsSubscriptionAdmin]

    def get(self, request):
        features = (
            "ADVANCED_ANALYTICS",
            "REPORTING",
            "FIELD_OPERATIONS",
            "ADVANCED_WORKFLOWS",
            "OFFICIAL_RECORDS",
            "CUSTOM_FORMS",
        )
        return Response({
            "features": {
                feature: SubscriptionService.has_feature(
                    request.user.company,
                    feature,
                )
                for feature in features
            }
        })

