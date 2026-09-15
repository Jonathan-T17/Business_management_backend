from django.db import transaction
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

        activity = FieldOperationService.start_activity(
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

        activity = FieldOperationService.complete_activity(
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

        visible_activities = VisibilityService.field_activities_queryset(
            user=user, queryset=FieldActivity.objects.all(),
        )
        return queryset.filter(activity__in=visible_activities)


    @action(detail=True,methods=['post'],url_path='start-form')
    @transaction.atomic
    def start_form(self,request,pk=None):
        from forms_engine.services import FormSubmissionService
        from company_setup.models import FieldActivityTemplate
        from rest_framework.generics import get_object_or_404
        stop=self.get_object()
        stop=FieldStop.objects.select_for_update().get(pk=stop.pk)
        if stop.activity.employee_id!=request.user.id or stop.status not in {'PENDING','ARRIVED'}:
            raise ValidationError('Only the assigned worker may start a form for an unfinished stop.')
        if stop.form_submission_id:
            return Response({'id':str(stop.form_submission_id)})
        configuration=get_object_or_404(FieldActivityTemplate,pk=request.data.get('configuration'),company=request.user.company,activity_type=stop.activity.activity_type,is_active=True)
        if not configuration.form_template_id:
            raise ValidationError('This configuration has no form.')
        submission=FormSubmissionService.create_submission(template=configuration.form_template,user=request.user,title=stop.location_name)
        stop.form_submission=submission;stop.save(update_fields=['form_submission'])
        return Response({'id':str(submission.pk)},status=201)

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

        stop = FieldOperationService.arrive_stop(
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

        stop = FieldOperationService.complete_stop(
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
