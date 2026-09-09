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

        user = self.request.user

        queryset = (
            CompanyPlan.objects
            .select_related(
                "company",
                "branch",
                "department",
                "created_by",
                "owner",
            )
            .prefetch_related(
                "items"
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            company=user.company
        )

        if user.role == Roles.ADMIN:
            return queryset

        profile = getattr(
            user,
            "employee_profile",
            None,
        )

        return queryset.filter(
            Q(visibility="COMPANY")
            |
            Q(owner=user)
            |
            Q(
                visibility="BRANCH",
                branch=user.branch,
            )
            |
            Q(
                visibility="DEPARTMENT",
                department=getattr(
                    profile,
                    "department",
                    None,
                ),
            )
        ).distinct()

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

        if user.role == Roles.SUPERUSER:
            return queryset

        return queryset.filter(
            plan__company=user.company
        )

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