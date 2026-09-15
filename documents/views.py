from django.db import transaction
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

from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)

from django.http import FileResponse

from core.roles import Roles
from core.capability_service import CapabilityService
from core.visibility import VisibilityService

from .models import (
    Attachment,
    DocumentCategory,
    Document,
)

from .serializers import (
    AttachmentSerializer,
    DocumentCategorySerializer,
    DocumentSerializer,
    DocumentVersionSerializer,
)

from .permissions import (
    CanManageDocuments,
    CanUseAttachments,
)

from .services import (
    DocumentService,
)


# ============================================================
# Attachments
# ============================================================

class AttachmentViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        AttachmentSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanUseAttachments,
    ]

    http_method_names = [
        "get",
        "post",
        "delete",
        "head",
        "options",
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            Attachment.objects
            .select_related(
                "company",
                "uploaded_by",
                "content_type",
            )
            .filter(
                is_active=True
            )
        )

        visible_ids = [
            attachment.id
            for attachment in queryset
            if VisibilityService.can_view_attachment(
                user=user,
                attachment=attachment,
            )
        ]

        return queryset.filter(
            id__in=visible_ids
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="download",
    )
    def download(
        self,
        request,
        pk=None,
    ):
        attachment = self.get_object()

        if not VisibilityService.can_view_attachment(
            user=request.user,
            attachment=attachment,
        ):
            raise PermissionDenied(
                "You cannot access this attachment."
            )

        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_filename,
        )

    @transaction.atomic
    def perform_destroy(
        self,
        instance,
    ):

        user = self.request.user

        if (
            user.role
            not in (
                Roles.ADMIN,
            )
            and instance.uploaded_by_id
            != user.id
        ):
            raise ValidationError(
                "You cannot remove "
                "this attachment."
            )

        if instance.content_type.app_label == 'forms_engine' and instance.content_type.model == 'formsubmission':
            from forms_engine.attachments import can_edit_files
            parent = instance.content_object
            parent = type(parent).objects.select_for_update().get(pk=parent.pk)
            if not can_edit_files(user, parent):
                raise ValidationError('Attachments are locked for this submission.')

        instance.is_active = False

        instance.save(
            update_fields=[
                "is_active"
            ]
        )


# ============================================================
# Document Categories
# ============================================================

class DocumentCategoryViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        DocumentCategorySerializer
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
            CanManageDocuments(),
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            DocumentCategory.objects
            .filter(
                is_active=True
            )
        )

        if not CapabilityService.is_tenant_identity(user):
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
                self.request.user.company
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


# ============================================================
# Documents
# ============================================================

class DocumentViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        DocumentSerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
            "download",
        ):
            return [
                IsAuthenticated()
            ]

        return [
            IsAuthenticated(),
            CanManageDocuments(),
        ]

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        from rest_framework.exceptions import NotFound
        from .access import DocumentAccessService
        from security.services import create_audit_log
        document = self.get_object()
        if not DocumentAccessService.can_download(user=request.user, document=document):
            raise PermissionDenied("You cannot download this document.")
        version = document.versions.filter(version_number=document.current_version).first()
        if not version or not version.file:
            raise NotFound("The current document file is unavailable.")
        try:
            stream = version.file.open("rb")
        except FileNotFoundError:
            raise NotFound("The current document file is unavailable.")
        try:
            create_audit_log(user=request.user, company=document.company, request=request,
                             action="DOWNLOAD", obj=document,
                             description="Document downloaded.", metadata={"version":version.version_number})
        except Exception:
            stream.close()
            raise
        response = FileResponse(stream, as_attachment=True, filename=version.original_filename,
                                content_type="application/octet-stream")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def get_queryset(self):

        queryset = (
            Document.objects
            .select_related(
                "company",
                "category",
                "branch",
                "department",
                "team",
                "owner",
                "created_by",
            )
            .prefetch_related(
                "versions"
            )
        )

        queryset = VisibilityService.documents_queryset(
            user=self.request.user,
            queryset=queryset,
        )

        category = (
            self.request
            .query_params
            .get("category")
        )

        status_filter = (
            self.request
            .query_params
            .get("status")
        )

        branch = (
            self.request
            .query_params
            .get("branch")
        )

        project = (
            self.request
            .query_params
            .get("project")
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        if category:
            queryset = queryset.filter(
                category_id=category
            )

        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        if branch:
            queryset = queryset.filter(
                branch_id=branch
            )

        if project:
            queryset = queryset.filter(
                project_id=project
            )

        if search:
            queryset = queryset.filter(
                title__icontains=search
            )

        return queryset

    def perform_destroy(
        self,
        instance,
    ):

        instance.status = "ARCHIVED"
        instance.is_active = False

        instance.save(
            update_fields=[
                "status",
                "is_active",
                "updated_at",
            ]
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="add-version",
    )
    def add_version(
        self,
        request,
        pk=None,
    ):

        document = (
            self.get_object()
        )

        file = request.FILES.get(
            "file"
        )

        if not file:
            raise ValidationError({
                "file":
                    "File is required."
            })

        version = (
            DocumentService.add_version(
                document=document,
                file=file,
                user=request.user,
                change_note=
                    request.data.get(
                        "change_note",
                        "",
                    ),
                request=request,
            )
        )

        return Response(
            DocumentVersionSerializer(
                version,
                context={
                    "request":
                        request
                },
            ).data,
            status=
                status.HTTP_201_CREATED,
        )