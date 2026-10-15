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
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from documents.serializers import AttachmentSerializer


class RequestFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

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

    search_fields = ['title', 'request_number']

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

    @extend_schema(methods=['GET'], responses=AttachmentSerializer(many=True))
    @extend_schema(methods=['POST'], request=RequestFileUploadSerializer, responses={201:AttachmentSerializer})
    @action(detail=True, methods=['get', 'post'], url_path='attachments', pagination_class=None)
    def attachments(self, request, pk=None):
        from django.contrib.contenttypes.models import ContentType
        from documents.models import Attachment
        from documents.serializers import AttachmentSerializer
        obj = self.get_object()
        content_type = ContentType.objects.get_for_model(obj)
        if request.method == 'POST':
            serializer = AttachmentSerializer(data={'content_type': content_type.pk, 'object_id': str(obj.pk), 'file': request.FILES.get('file')}, context={'request': request})
            serializer.is_valid(raise_exception=True)
            attachment = serializer.save()
            return Response(AttachmentSerializer(attachment, context={'request':request}).data, status=201)
        files = Attachment.objects.filter(company=obj.company, content_type=content_type, object_id=str(obj.pk), is_active=True).order_by('created_at','pk')
        return Response(AttachmentSerializer(files, many=True, context={'request':request}).data)

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


    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        from .services import BusinessRequestLifecycleService
        obj = BusinessRequestLifecycleService.finish(request_obj=self.get_object(), actor=request.user,
            action="CANCEL", reason=request.data.get("reason", ""), request=request)
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .services import BusinessRequestLifecycleService
        obj = BusinessRequestLifecycleService.finish(request_obj=self.get_object(), actor=request.user,
            action="CLOSE", request=request)
        return Response(self.get_serializer(obj).data)

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

        from .services import BusinessRequestLifecycleService
        business_request = BusinessRequestLifecycleService.fulfill(
            request_obj=business_request, actor=request.user, request=request,
            note=request.data.get("note", ""))

        return Response(
            self.get_serializer(
                business_request
            ).data
        )
