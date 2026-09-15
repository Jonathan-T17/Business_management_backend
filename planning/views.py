from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.roles import Roles

from .models import (
    CompanyPlan,
    PlanItem,
)

from .serializers import (
    CompanyPlanSerializer,
    PlanItemSerializer,
)

from .permissions import (
    CanManagePlans,
)


class CompanyPlanViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        CompanyPlanSerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            CanManagePlans(),
        ]

    def get_queryset(self):

        from .access import PlanningAccessService
        return PlanningAccessService.queryset(
            user=self.request.user,
            queryset=CompanyPlan.objects.select_related("company", "branch", "department", "owner", "created_by").prefetch_related("items"),
        )

    def _transition(self, status):
        from .services import PlanningService
        plan = PlanningService.transition(plan=self.get_object(), user=self.request.user,
                                          to_status=status, request=self.request)
        return Response(self.get_serializer(plan).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        return self._transition("ACTIVE")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition("COMPLETED")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition("CANCELLED")

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._transition("ARCHIVED")

    def perform_create(
        self,
        serializer,
    ):

        serializer.save(
            company=
                self.request.user.company,
            created_by=
                self.request.user,
        )


class PlanItemViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        PlanItemSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanManagePlans,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            PlanItem.objects
            .select_related(
                "plan",
                "plan__company",
                "owner",
                "project",
                "task",
            )
        )

        from .access import PlanningAccessService
        visible_plans = PlanningAccessService.queryset(user=user, queryset=CompanyPlan.objects.all())
        return queryset.filter(plan__in=visible_plans)

    def perform_create(
        self,
        serializer,
    ):

        plan = serializer.validated_data[
            "plan"
        ]

        serializer.save(
            plan=plan
        )