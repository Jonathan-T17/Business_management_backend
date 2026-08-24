from django.db.models import QuerySet

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles

from .models import ActivityLog
from .serializers import ActivityLogSerializer


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only activity feed for the authenticated user's company.

    Supported endpoints:

        GET /activity/
        GET /activity/{id}/
        GET /activity/recent/
        GET /activity/project/{project_id}/
        GET /activity/task/{task_id}/

    Optional filters:

        ?project=<id>
        ?task=<id>
        ?user=<id>
        ?action=<ACTION>
    """

    serializer_class = ActivityLogSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        user = self.request.user

        if not user.is_authenticated:
            return ActivityLog.objects.none()

        company = getattr(
            user,
            "company",
            None,
        )

        if company is None:
            return ActivityLog.objects.none()

        queryset = (
            ActivityLog.objects
            .filter(company=company)
            .select_related(
                "company",
                "project",
                "task",
                "user",
            )
            .order_by("-created_at")
        )

        # -----------------------------------------------------
        # Optional filters
        # -----------------------------------------------------

        project_id = self.request.query_params.get(
            "project"
        )

        if project_id:
            queryset = queryset.filter(
                project_id=project_id
            )

        task_id = self.request.query_params.get(
            "task"
        )

        if task_id:
            queryset = queryset.filter(
                task_id=task_id
            )

        user_id = self.request.query_params.get(
            "user"
        )

        if user_id:
            queryset = queryset.filter(
                user_id=user_id
            )

        action_name = self.request.query_params.get(
            "action"
        )

        if action_name:
            queryset = queryset.filter(
                action=action_name
            )

        # -----------------------------------------------------
        # Branch-level restriction
        # -----------------------------------------------------
        #
        # Project activity is already tenant-isolated.
        # For managers and employees, restrict activity to
        # projects they can access through project membership.
        #
        # Company admins/superusers can see company activity.
        # -----------------------------------------------------

        if user.role in (
            Roles.MANAGER,
            Roles.EMPLOYEE,
        ):
            queryset = queryset.filter(
                project__memberships__user=user
            ).distinct()

        return queryset

    # ---------------------------------------------------------
    # Recent activity
    # ---------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="recent",
    )
    def recent(self, request):
        """
        Return the most recent activity records.

        Default: 20 records.
        Maximum: 100 records.
        """

        try:
            limit = int(
                request.query_params.get(
                    "limit",
                    20,
                )
            )
        except (TypeError, ValueError):
            limit = 20

        limit = max(
            1,
            min(limit, 100),
        )

        queryset = self.get_queryset()[:limit]

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    # ---------------------------------------------------------
    # Project activity
    # ---------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path=r"project/(?P<project_id>[^/.]+)",
    )
    def project_activity(
        self,
        request,
        project_id=None,
    ):
        """
        Return activity for a specific project.

        Visibility is still controlled by get_queryset().
        """

        queryset = self.get_queryset().filter(
            project_id=project_id
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )
            return self.get_paginated_response(
                serializer.data
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    # ---------------------------------------------------------
    # Task activity
    # ---------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path=r"task/(?P<task_id>[^/.]+)",
    )
    def task_activity(
        self,
        request,
        task_id=None,
    ):
        """
        Return activity for a specific task.
        """

        queryset = self.get_queryset().filter(
            task_id=task_id
        )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(
                page,
                many=True,
            )
            return self.get_paginated_response(
                serializer.data
            )

        serializer = self.get_serializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)