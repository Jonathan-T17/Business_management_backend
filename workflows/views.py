from django.db.models import Q

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.roles import Roles
from core.capability_service import CapabilityService
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
from .runtime_service import WorkflowRuntimeService


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

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

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

        if not CapabilityService.is_tenant_identity(user):
            return queryset.none()

        queryset = queryset.filter(
            company=user.company
        )

        from core.position_scope import PositionScope
        from workflows.models import WorkflowStepRecipient
        recipients = WorkflowStepRecipient.objects.filter(
            step__workflow_instance__company=user.company
        )
        current = PositionScope.current_recipients(recipients.filter(user=user))
        visible = Q(submitted_by=user) | Q(steps__recipients__id__in=current.values("pk"))
        for target_type, permission in WorkflowService.WORKFLOW_DELEGATION_PERMISSIONS.items():
            delegated = PositionScope.current_recipients(recipients.filter(
                user_id__in=VisibilityService.delegated_user_ids(user=user, permission=permission),
                step__workflow_instance__workflow__target_type=target_type,
            ))
            visible |= Q(steps__recipients__id__in=delegated.values("pk"))
        return queryset.filter(visible).distinct()

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

        WorkflowRuntimeService.approve(
            instance=instance,
            actor=request.user,
            request=request,
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

        WorkflowRuntimeService.reject(
            instance=instance,
            actor=request.user,
            request=request,
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

        WorkflowRuntimeService.return_for_changes(
            instance=instance,
            actor=request.user,
            request=request,
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
