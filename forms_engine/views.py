from django.db import transaction
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from core.roles import Roles
from core.visibility import VisibilityService
from security.services import create_audit_log

from workflows.models import (
    WorkflowDefinition,
    WorkflowInstance,
)

from .models import (
    FormTemplate,
    FormSubmission,
)

from .serializers import (
    FormTemplateSerializer,
    FormSubmissionSerializer,
)

from .permissions import (
    CanManageFormTemplates,
    CanUseForms,
)

from .services import (
    FormSubmissionService,
)


# ============================================================
# Form Templates
# ============================================================

class FormTemplateViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FormTemplateSerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanUseForms(),
            ]

        return [
            IsAuthenticated(),
            CanManageFormTemplates(),
        ]

    def get_queryset(self):

        from .access import FormAccess
        queryset=FormAccess.templates(self.request.user,FormTemplate.objects.select_related('company','workflow').prefetch_related('fields'),builder=self.request.query_params.get('mode')=='builder' or self.action not in {'list','retrieve'})
        if self.request.query_params.get('mode')=='builder' or self.action=='retrieve':
            queryset=FormAccess.templates(self.request.user,FormTemplate.objects.select_related('company','workflow').prefetch_related('fields'),builder=True)
        category=self.request.query_params.get('category')
        return queryset.filter(category=category) if category else queryset

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

    def perform_update(self, serializer):
        template = serializer.save()
        create_audit_log(user=self.request.user, company=template.company, request=self.request, action="UPDATE", description=f"Updated form template: {template.name}.", obj=template)

    def perform_destroy(self, instance):
        from .versioning import FormTemplateVersionService
        FormTemplateVersionService.retire(template=instance,actor=self.request.user)

    @action(detail=True,methods=['post'])
    def publish(self,request,pk=None):
        from .versioning import FormTemplateVersionService
        return Response(self.get_serializer(FormTemplateVersionService.publish(template=self.get_object(),actor=request.user)).data)

    @action(detail=True,methods=['post'])
    def archive(self,request,pk=None):
        from .versioning import FormTemplateVersionService
        return Response(self.get_serializer(FormTemplateVersionService.retire(template=self.get_object(),actor=request.user)).data)

    @action(detail=True,methods=['post'])
    def copy(self,request,pk=None):
        from rest_framework import serializers
        from .versioning import FormTemplateVersionService
        class Input(serializers.Serializer):
            name=serializers.CharField(max_length=255)
            code=serializers.SlugField(max_length=100)
        values=Input(data=request.data);values.is_valid(raise_exception=True)
        target=FormTemplateVersionService.copy(template=self.get_object(),actor=request.user,**values.validated_data)
        return Response(self.get_serializer(target).data,status=201)

    @action(detail=True,methods=['post'],url_path='reorder-fields')
    def reorder_fields(self,request,pk=None):
        from .versioning import FormTemplateVersionService
        template=self.get_object()
        ids=request.data.get('field_ids')
        fields=FormTemplateVersionService.field_data(template)
        existing=list(template.fields.all())
        if not isinstance(ids,list) or len(ids)!=len(existing) or set(map(str,ids))!={str(f.pk) for f in existing}:
            raise ValidationError('Supply each field exactly once.')
        by_id={str(f.pk):data for f,data in zip(existing,fields)}
        target=FormTemplateVersionService.revise(template=template,actor=request.user,data={},fields=[by_id[str(pk)] for pk in ids])
        return Response(self.get_serializer(target).data)

    @action(detail=False,methods=['get'],permission_classes=[IsAuthenticated])
    def request_types(self,request):
        from company_setup.models import RequestTypeDefinition
        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(request.user):
            raise ValidationError('Company context required.')
        return Response(list(RequestTypeDefinition.objects.filter(company=request.user.company,is_active=True).values('id','code','name','amount_enabled','quantity_enabled','needed_by_enabled','form_template_id')))

    @action(detail=False,methods=['get'])
    def choices(self,request):
        from companies.models import Branch
        from organizations.models import Department, Team
        company=request.user.company
        from django.contrib.auth import get_user_model
        return Response({
            'people': [{'id':str(u.pk),'name':u.full_name or str(u.pk)} for u in get_user_model().objects.filter(company=company,is_active=True,role__in=['ADMIN','MANAGER','EMPLOYEE']).only('id','full_name')],
            'branches':list(Branch.objects.filter(company=company).values('id','name')),
            'departments':list(Department.objects.filter(company=company).values('id','name')),
            'teams':list(Team.objects.filter(company=company).values('id','name')),
            'workflows':list(WorkflowDefinition.objects.filter(company=company,target_type='FORM_SUBMISSION',lifecycle_status='PUBLISHED',is_active=True).values('id','name')),
        })

    @action(detail=False,methods=['get'])
    def starters(self,request):
        from .models import FormStarter
        return Response([{'code':s.code,'name':s.name,'description':s.description,'category':s.category,'allow_drafts':True,'fields':s.field_schema} for s in FormStarter.objects.filter(is_active=True).order_by('name')])


# ============================================================
# Form Submissions
# ============================================================

class FormSubmissionViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FormSubmissionSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanUseForms,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FormSubmission.objects
            .select_related(
                "company",
                "template",
                "submitted_by",
                "branch",
                "department",
                "team",
                "project",
                "task",
            )
        )

        return VisibilityService.form_submissions_queryset(
            user=user,
            queryset=queryset,
        )

    @action(detail=True, methods=['get', 'post'])
    def attachments(self, request, pk=None):
        from django.db import transaction
        from documents.services import AttachmentService, validate_uploaded_file, MAX_ATTACHMENT_SIZE
        from .attachments import can_read_files, can_edit_files, can_upload_files
        from rest_framework.exceptions import PermissionDenied
        with transaction.atomic():
            submission = self.get_object()
            submission = FormSubmission.objects.select_for_update().get(pk=submission.pk)
            if request.method == 'POST':
                if not can_upload_files(request.user, submission):
                    raise PermissionDenied('Attachments are locked for this submission.')
                uploaded = request.FILES.get('file')
                mime = validate_uploaded_file(uploaded, max_size=MAX_ATTACHMENT_SIZE)
                attachment = AttachmentService.create(actor=request.user, parent=submission, file=uploaded,
                    original_filename=uploaded.name, mime_type=mime, file_size=uploaded.size)
                create_audit_log(user=request.user, company=submission.company, action='UPDATE', obj=submission, description='Added form attachment.')
                return Response({'id': str(attachment.pk)}, status=201)
            visible = can_read_files(request.user, submission)
            return Response({'can_upload': can_upload_files(request.user, submission), 'can_remove': can_edit_files(request.user, submission), 'restricted': not visible,
                'files': [{'id':str(item.pk), 'name':item.original_filename, 'size':item.file_size}
                    for item in submission.attachments.filter(is_active=True)] if visible else []})

    @action(detail=True, methods=['get', 'delete'], url_path=r'attachments/(?P<attachment_id>[0-9a-fA-F-]{36})')
    def attachment(self, request, pk=None, attachment_id=None):
        from django.db import transaction
        from django.shortcuts import get_object_or_404
        from django.http import FileResponse
        from .attachments import can_read_files, can_edit_files
        from rest_framework.exceptions import PermissionDenied
        with transaction.atomic():
            submission = self.get_object()
            submission = FormSubmission.objects.select_for_update().get(pk=submission.pk)
            attachment = get_object_or_404(submission.attachments.filter(is_active=True), pk=attachment_id)
            if request.method == 'DELETE':
                if not can_edit_files(request.user, submission):
                    raise PermissionDenied('Attachments are locked for this submission.')
                attachment.is_active = False
                attachment.save(update_fields=['is_active'])
                create_audit_log(user=request.user, company=submission.company, action='UPDATE', obj=submission, description='Removed form attachment.')
                return Response(status=204)
            if not can_read_files(request.user, submission):
                raise PermissionDenied('This attachment contains restricted information.')
            return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.original_filename)

    def perform_destroy(
        self,
        instance,
    ):

        if hasattr(instance, 'business_request'):
            raise ValidationError('Manage this form through its business request.')

        if instance.status != "DRAFT":
            raise ValidationError(
                "Only draft submissions "
                "can be deleted."
            )

        if (
            instance.submitted_by_id
            != self.request.user.id
        ):
            raise ValidationError(
                "Only the author can delete "
                "this draft."
            )

        instance.delete()

    # --------------------------------------------------------
    # Submit
    # --------------------------------------------------------

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

        submission = (
            self.get_object()
        )

        workflow = None

        workflow_id = (
            request.data.get(
                "workflow"
            )
        )

        if workflow_id and str(workflow_id)!=str(submission.template.workflow_id):
            raise ValidationError('The published template determines the approval workflow.')

        submission, instance = (
            FormSubmissionService.submit(
                submission=submission,
                user=request.user,
                workflow=workflow,
            )
        )

        return Response(
            {
                "message":
                    "Submission submitted successfully.",

                "submission":
                    self.get_serializer(
                        submission
                    ).data,

                "workflow_instance":
                    instance.id if instance else None,
            },
            status=
                status.HTTP_200_OK,
        )
