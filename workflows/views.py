from django.db.models import Q

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles
from core.visibility import VisibilityService

from .models import (
    WorkflowDefinition,
    WorkflowInstance,
)

from .serializers import (
    WorkflowDefinitionSerializer,
    WorkflowInstanceSerializer,
)

from .permissions import (
    CanManageWorkflows,
    CanViewWorkflow,
)

from .services import (
    WorkflowService,
)


# ============================================================
# Workflow Templates
# ============================================================

class WorkflowDefinitionViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        WorkflowDefinitionSerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanViewWorkflow(),
            ]

        return [
            IsAuthenticated(),
            CanManageWorkflows(),
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            WorkflowDefinition.objects
            .prefetch_related(
                "steps"
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        if not user.company_id:
            return queryset.none()

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


# ============================================================
# Workflow Runtime
# ============================================================

class WorkflowInstanceViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        WorkflowInstanceSerializer
    )

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            WorkflowInstance.objects
            .select_related(
                "workflow",
                "company",
                "submitted_by",
                "content_type",
            )
            .prefetch_related(
                "steps__recipients__user",
                "action_logs__actor",
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        queryset = queryset.filter(
            company=user.company
        )

        if user.role == Roles.ADMIN:
            return queryset

        recipient_ids = {user.id}
        for permission in (
            "APPROVE_REPORTS",
            "APPROVE_REQUESTS",
            "REVIEW_SUBMISSIONS",
        ):
            recipient_ids.update(
                VisibilityService.delegated_user_ids(
                    user=user,
                    permission=permission,
                )
            )

        return queryset.filter(
            Q(submitted_by=user)
            | Q(steps__recipients__user_id__in=recipient_ids)
        ).distinct()

    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(
        self,
        request,
        pk=None,
    ):

        instance = self.get_object()

        WorkflowService.approve(
            instance=instance,
            user=request.user,
            note=request.data.get(
                "note",
                "",
            ),
        )

        instance.refresh_from_db()

        return Response(
            self.get_serializer(
                instance
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(
        self,
        request,
        pk=None,
    ):

        instance = self.get_object()

        WorkflowService.reject(
            instance=instance,
            user=request.user,
            note=request.data.get(
                "note",
                "",
            ),
        )

        instance.refresh_from_db()

        return Response(
            self.get_serializer(
                instance
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="return",
    )
    def return_for_correction(
        self,
        request,
        pk=None,
    ):

        instance = self.get_object()

        WorkflowService.return_for_correction(
            instance=instance,
            user=request.user,
            note=request.data.get(
                "note",
                "",
            ),
        )

        instance.refresh_from_db()

        return Response(
            self.get_serializer(
                instance
            ).data
        )