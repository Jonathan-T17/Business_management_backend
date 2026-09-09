from django.utils import timezone

from rest_framework import (
    status,
    viewsets,
)

from rest_framework.decorators import (
    action,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import (
    Response,
)

from core.roles import Roles
from core.visibility import VisibilityService

from .models import (
    FieldActivity,
    FieldStop,
)

from .serializers import (
    FieldActivitySerializer,
    FieldStopSerializer,
)

from .permissions import (
    CanUseFieldOperations,
    CanManageFieldOperations,
)

from .services import (
    FieldOperationService,
    FieldSummaryService,
)


class FieldActivityViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FieldActivitySerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
            "start",
            "complete",
            "my_today",
            "daily_summary",
        ):
            return [
                IsAuthenticated(),
                CanUseFieldOperations(),
            ]

        return [
            IsAuthenticated(),
            CanManageFieldOperations(),
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FieldActivity.objects
            .select_related(
                "company",
                "branch",
                "department",
                "employee",
                "project",
                "task",
                "created_by",
            )
            .prefetch_related(
                "stops__metrics"
            )
        )

        return VisibilityService.field_activities_queryset(
            user=user,
            queryset=queryset,
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

        activity = self.get_object()

        FieldOperationService.start_activity(
            activity=activity,
            user=request.user,
            latitude=
                request.data.get(
                    "latitude"
                ),
            longitude=
                request.data.get(
                    "longitude"
                ),
            request=request,
        )

        return Response(
            self.get_serializer(
                activity
            ).data
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(
        self,
        request,
        pk=None,
    ):

        activity = self.get_object()

        FieldOperationService.complete_activity(
            activity=activity,
            user=request.user,
            latitude=
                request.data.get(
                    "latitude"
                ),
            longitude=
                request.data.get(
                    "longitude"
                ),
            request=request,
        )

        return Response(
            self.get_serializer(
                activity
            ).data
        )


    @action(
        detail=False,
        methods=["get"],
        url_path="my-today",
    )
    def my_today(
        self,
        request,
    ):

        today = timezone.localdate()

        activities = (
            self.get_queryset()
            .filter(
                employee=request.user,
                activity_date=today,
            )
        )

        return Response(
            self.get_serializer(
                activities,
                many=True,
            ).data
        )


    @action(
        detail=False,
        methods=["get"],
        url_path="daily-summary",
    )
    def daily_summary(
        self,
        request,
    ):

        requested_date = (
            request.query_params
            .get("date")
        )

        if requested_date:
            from datetime import date

            target_date = (
                date.fromisoformat(
                    requested_date
                )
            )
        else:
            target_date = (
                timezone.localdate()
            )

        return Response(
            FieldSummaryService
            .employee_daily_summary(
                user=request.user,
                target_date=
                    target_date,
            )
        )


class FieldStopViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FieldStopSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanUseFieldOperations,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FieldStop.objects
            .select_related(
                "activity",
                "activity__company",
                "activity__employee",
            )
            .prefetch_related(
                "metrics"
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            activity__company=user.company
        )

        if user.role == Roles.ADMIN:
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(
                activity__branch=
                    user.branch
            )

        return queryset.filter(
            activity__employee=user
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="arrive",
    )
    def arrive(
        self,
        request,
        pk=None,
    ):

        stop = self.get_object()

        FieldOperationService.arrive_stop(
            stop=stop,
            user=request.user,
            latitude=
                request.data.get(
                    "latitude"
                ),
            longitude=
                request.data.get(
                    "longitude"
                ),
            request=request,
        )

        return Response(
            self.get_serializer(
                stop
            ).data
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
    )
    def complete(
        self,
        request,
        pk=None,
    ):

        stop = self.get_object()

        FieldOperationService.complete_stop(
            stop=stop,
            user=request.user,
            notes=
                request.data.get(
                    "notes",
                    "",
                ),
            request=request,
        )

        return Response(
            self.get_serializer(
                stop
            ).data
        )