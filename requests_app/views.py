from django.db.models import Q

from rest_framework import (
    status,
    viewsets,
)

from rest_framework.decorators import action

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import Response

from rest_framework.exceptions import (
    ValidationError,
)

from core.roles import Roles
from core.visibility import VisibilityService

from .models import BusinessRequest

from .serializers import (
    BusinessRequestSerializer,
)

from .services import (
    BusinessRequestService,
)

from .permissions import (
    CanApproveRequests,
)


class BusinessRequestViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        BusinessRequestSerializer
    )

    permission_classes = [
        IsAuthenticated,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            BusinessRequest.objects
            .select_related(
                "company",
                "branch",
                "department",
                "requester",
                "project",
                "task",
                "workflow",
            )
        )

        return VisibilityService.business_requests_queryset(
            user=user,
            queryset=queryset,
        )

    def perform_destroy(
        self,
        instance,
    ):

        if instance.status != "DRAFT":
            raise ValidationError(
                "Only draft requests can be deleted."
            )

        if (
            instance.requester_id
            != self.request.user.id
        ):
            raise ValidationError(
                "Only the requester can delete this draft."
            )

        instance.delete()


    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(
        self,
        request,
        pk=None,
    ):

        business_request = (
            self.get_object()
        )

        business_request, workflow = (
            BusinessRequestService.submit(
                business_request=
                    business_request,
                user=request.user,
            )
        )

        return Response(
            {
                "message":
                    "Request submitted successfully.",

                "request":
                    self.get_serializer(
                        business_request
                    ).data,

                "workflow_instance":
                    workflow.id,
            }
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="fulfill",
        permission_classes=[
            IsAuthenticated,
            CanApproveRequests,
        ],
    )
    def fulfill(
        self,
        request,
        pk=None,
    ):

        business_request = (
            self.get_object()
        )

        BusinessRequestService.mark_fulfilled(
            business_request=
                business_request,
            user=request.user,
        )

        return Response(
            self.get_serializer(
                business_request
            ).data
        )