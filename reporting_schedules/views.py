from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles

from .models import (
    ReportingSchedule,
    ReportingObligation,
)

from .serializers import (
    ReportingScheduleSerializer,
    ReportingObligationSerializer,
)

from .permissions import (
    CanManageReportingSchedules,
    CanViewReportingObligations,
)

from .services import (
    ReportingScheduleService,
    ReportingObligationService,
)


class ReportingScheduleViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        ReportingScheduleSerializer
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
            CanManageReportingSchedules(),
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            ReportingSchedule.objects
            .select_related(
                "company",
                "template",
                "target_user",
                "target_branch",
                "target_department",
                "target_team",
                "target_position",
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        return queryset.filter(
            company=user.company
        )

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

    def perform_destroy(
        self,
        instance,
    ):

        instance.is_active = False

        instance.save(
            update_fields=[
                "is_active"
            ]
        )


class ReportingObligationViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        ReportingObligationSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanViewReportingObligations,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            ReportingObligation.objects
            .select_related(
                "company",
                "schedule",
                "schedule__template",
                "user",
                "submission",
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            company=user.company
        )

        if user.role == Roles.ADMIN:
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(
                Q(user__branch=user.branch)
                |
                Q(user=user)
            ).distinct()

        return queryset.filter(
            user=user
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="mine",
    )
    def mine(
        self,
        request,
    ):

        obligations = (
            self.get_queryset()
            .filter(
                user=request.user
            )
        )

        return Response(
            self.get_serializer(
                obligations,
                many=True,
            ).data
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="due-today",
    )
    def due_today(
        self,
        request,
    ):

        today = (
            timezone.localdate()
        )

        obligations = (
            self.get_queryset()
            .filter(
                reporting_date=today
            )
        )

        return Response(
            self.get_serializer(
                obligations,
                many=True,
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="start",
    )
    def start(
        self,
        request,
        pk=None,
    ):

        obligation = (
            self.get_object()
        )

        submission = (
            ReportingObligationService
            .start_submission(
                obligation=
                    obligation,
                user=
                    request.user,
            )
        )

        return Response(
            {
                "submission_id":
                    str(
                        submission.id
                    ),

                "message":
                    "Reporting draft started.",
            },
            status=
                status.HTTP_200_OK,
        )