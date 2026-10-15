from django.db import transaction
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema
from company_setup.serializers import RequestTypeChoiceSerializer
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
    LibraryUpdateSerializer,
)

from .permissions import (
    CanManageFormTemplates,
    CanUseForms,
    CanUseFormSubmissions,
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
            "initial_values",
            "request_types",
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
        queryset=FormAccess.templates(self.request.user,FormTemplate.objects.select_related('company','workflow').prefetch_related('fields'),builder=self.request.query_params.get('mode')=='builder' or self.action not in {'list','retrieve','initial_values'})
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
        FormTemplateVersionService.delete_from_workspace(template=instance,actor=self.request.user)

    @extend_schema(responses={200: {"type":"object","properties":{"values":{"type":"object","additionalProperties":True},"entry_branch":{"type":"object","nullable":True,"properties":{"id":{"type":"integer"},"name":{"type":"string"}},"required":["id","name"]},"branch_choices":{"type":"array","items":{"type":"object","properties":{"id":{"type":"integer"},"name":{"type":"string"}},"required":["id","name"]}}},"required":["values","entry_branch","branch_choices"]}})
    @action(detail=True, methods=['get'], url_path='initial-values')
    def initial_values(self, request, pk=None):
        from .defaults import initial_values
        template = self.get_object()
        from .access import FormAccess
        if not FormAccess.eligible(request.user, template):
            raise ValidationError('This form is not available for use.')
        schema = FormSubmissionService.build_schema_snapshot(template)
        branch = FormAccess.starting_branch(request.user, template)
        choices = list(FormAccess.filing_branches(request.user, template).values('id', 'name'))
        selected = request.query_params.get('branch')
        if selected is not None:
            choice = next((item for item in choices if str(item['id']) == selected), None)
            if choice is None:
                raise ValidationError({'branch': 'Choose an available entry branch.'})
            from companies.models import Branch
            branch = Branch.objects.get(pk=choice['id'], company_id=request.user.company_id)
        return Response({
            'values': initial_values(schema, request.user, branch=branch),
            'entry_branch': {'id': branch.pk, 'name': branch.name} if branch else None,
            'branch_choices': choices,
        })

    @extend_schema(request=LibraryUpdateSerializer, responses=FormTemplateSerializer)
    @action(detail=True, methods=['post'], url_path='apply-library-update')
    @transaction.atomic
    def apply_library_update(self, request, pk=None):
        from .catalogue import proposal
        from .versioning import FormTemplateVersionService
        template = self.get_object()
        type(template.company).objects.select_for_update().get(pk=template.company_id)
        template = FormTemplate.objects.select_for_update().get(pk=template.pk)
        input_serializer = LibraryUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        update = proposal(template)
        if not update or not update['available']:
            raise ValidationError('No newer library template is available.')
        if input_serializer.validated_data['signature'] != update['signature'] or input_serializer.validated_data['version'] != template.version:
            raise ValidationError('The form or template changed. Refresh and review the update again.')
        result = FormTemplateVersionService.revise(template=template, actor=request.user, data=update['data'], fields=update['fields'])
        return Response(self.get_serializer(result).data)

    @action(detail=True,methods=['post'])
    def publish(self,request,pk=None):
        from .versioning import FormTemplateVersionService
        publication = None
        if request.data:
            from rest_framework import serializers
            class Publication(serializers.Serializer):
                audience = serializers.ChoiceField(choices=['COMPANY', 'HEADQUARTERS', 'BRANCHES'])
                branch_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
                entry_visibility = serializers.ChoiceField(choices=['STANDARD', 'AUDIENCE'], default='STANDARD')
                share_confidential = serializers.BooleanField(default=False)
                confirm_confidential_access = serializers.BooleanField(default=False)
                preserve_restrictions = serializers.BooleanField(default=True)
                confirm_audience_change = serializers.BooleanField(default=False)
                confirm_no_approval = serializers.BooleanField(default=False)
            values = Publication(data=request.data); values.is_valid(raise_exception=True)
            publication = values.validated_data
        return Response(self.get_serializer(FormTemplateVersionService.publish(template=self.get_object(),actor=request.user,publication=publication)).data)

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

    @extend_schema(responses=RequestTypeChoiceSerializer(many=True))
    @action(detail=False,methods=['get'],permission_classes=[IsAuthenticated],pagination_class=None)
    def request_types(self,request):
        from company_setup.models import RequestTypeDefinition
        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(request.user):
            raise ValidationError('Company context required.')
        return Response(list(RequestTypeDefinition.objects.filter(company=request.user.company,is_active=True).values('id','code','name','description','sensitive','amount_enabled','amount_required','quantity_enabled','quantity_required','needed_by_enabled','needed_by_required','attachments_allowed','attachments_required','form_template_id')))

    @action(detail=False,methods=['get'])
    def choices(self,request):
        from companies.models import Branch
        from organizations.models import Department, Team
        company=request.user.company
        from django.contrib.auth import get_user_model
        from organizations.models import Position
        return Response({
            'people': [{'id':str(u.pk),'name':u.full_name or str(u.pk)} for u in get_user_model().objects.filter(company=company,is_active=True,role__in=['ADMIN','MANAGER','EMPLOYEE']).only('id','full_name')],
            'branches':list(Branch.objects.filter(company=company).values('id','name')),
            'departments':list(Department.objects.filter(company=company).values('id','name')),
            'teams':list(Team.objects.filter(company=company).values('id','name')),
            'workflows':list(WorkflowDefinition.objects.filter(company=company,target_type='FORM_SUBMISSION',is_active=True).values('id','name')),
            'headquarters_positions':list(Position.objects.filter(company=company, is_active=True, primary_scope='COMPANY').filter(Q(branch_id=company.headquarters_id) | Q(branch__isnull=True)).values('id','title')),
            'positions':list(Position.objects.filter(company=company, is_active=True).values('id','title')),
        })

    @action(detail=True, methods=['post'], url_path='configure-review')
    @transaction.atomic
    def configure_review(self, request, pk=None):
        import uuid
        from rest_framework import serializers
        from organizations.models import Position
        from workflows.models import WorkflowStepDefinition
        from core.capability_service import CapabilityService
        from core.capabilities import Capabilities
        from rest_framework.exceptions import PermissionDenied
        from .versioning import FormTemplateVersionService
        class Route(serializers.Serializer):
            route = serializers.ChoiceField(choices=['SUPERVISOR', 'HEADQUARTERS', 'SUPERVISOR_HEADQUARTERS'])
            headquarters_position = serializers.IntegerField(required=False)
        values = Route(data=request.data); values.is_valid(raise_exception=True)
        template = self.get_object()
        if not all(CapabilityService.has(request.user, capability) for capability in (Capabilities.MANAGE_WORKFLOWS, Capabilities.PUBLISH_WORKFLOWS)):
            raise PermissionDenied('Review-route management and publishing permission are required.')
        route = values.validated_data['route']
        if route == 'HEADQUARTERS' and not (template.audience_user_ids or template.audience_position_ids):
            raise ValidationError({'route':'Choose the permitted positions or people in the form access settings before allowing direct headquarters reporting.'})
        steps = []
        if route != 'HEADQUARTERS':
            steps.append({'name':'Assigned supervisor review', 'recipient_type':'REPORTER_MANAGER', 'notify_email':False})
        if route != 'SUPERVISOR':
            if not request.user.company.headquarters_id:
                raise ValidationError({'headquarters_position':'Set up your company headquarters first.'})
            position = Position.objects.filter(pk=values.validated_data.get('headquarters_position'), company=request.user.company,
                is_active=True, primary_scope='COMPANY').filter(Q(branch_id=request.user.company.headquarters_id) | Q(branch__isnull=True)).first()
            if not position:
                raise ValidationError({'headquarters_position':'Choose an active headquarters position with company-wide responsibility.'})
            steps.append({'name':f'Headquarters: {position.title}', 'recipient_type':'POSITION', 'recipient_position':position, 'notify_email':False})
        definition = WorkflowDefinition.objects.create(company=request.user.company, created_by=request.user,
            name=f'{template.name} review'[:255], code=f'form-review-{uuid.uuid4().hex}', description=f'Company form route: {route}', target_type='FORM_SUBMISSION', is_active=True)
        for order, step in enumerate(steps, 1):
            WorkflowStepDefinition.objects.create(workflow=definition, order=order, **step)
        create_audit_log(user=request.user, company=request.user.company, request=request, action='CREATE',
            description=f'Configured company form review route: {route}.', obj=definition)
        target = FormTemplateVersionService.revise(template=template, actor=request.user, data={'workflow':definition})
        return Response(self.get_serializer(target).data)

    @action(detail=False,methods=['get'])
    def starters(self,request):
        from .models import FormStarter
        return Response([{'code':s.code,'name':s.name,'description':s.description,'category':s.category,'allow_drafts':True,'fields':s.field_schema} for s in FormStarter.objects.filter(is_active=True).order_by('name')])

    @action(detail=False, methods=['post'], url_path='select-starters')
    @transaction.atomic
    def select_starters(self, request):
        from rest_framework import serializers
        from .models import FormStarter
        from .versioning import FormTemplateVersionService
        class Selection(serializers.Serializer):
            codes = serializers.ListField(child=serializers.SlugField(max_length=100), min_length=1, max_length=40)
        selection = Selection(data=request.data)
        selection.is_valid(raise_exception=True)
        codes = list(dict.fromkeys(selection.validated_data['codes']))
        starters = {s.code:s for s in FormStarter.objects.filter(is_active=True, code__in=codes)}
        if len(starters) != len(codes):
            raise ValidationError({'codes':'Choose available templates from the library.'})
        # Serialize selections for this tenant and never overwrite an existing company form.
        type(request.user.company).objects.select_for_update().get(pk=request.user.company_id)
        created, existing = [], []
        for code in codes:
            versions = FormTemplate.objects.filter(company=request.user.company, code=code)
            current = versions.filter(workspace_deleted=False).exclude(lifecycle_status='ARCHIVED').order_by('-version').first()
            if current:
                existing.append(current)
                continue
            starter = starters[code]
            fields = self.serializer_class().fields['fields']
            validated_fields = fields.run_validation(starter.field_schema)
            previous = versions.order_by('-version').first()
            if previous:
                # A removed selection may be chosen again from the current library.
                # Preserve historical versions and do not restore old assignments.
                from .catalogue import snapshot
                target = FormTemplateVersionService.revise(
                    template=previous, actor=request.user,
                    data={'name':starter.name, 'description':starter.description,
                          'category':starter.category, 'allow_drafts':True,
                          'source_starter':code, 'source_starter_snapshot':snapshot(starter),
                          'workflow':None, 'branch':None, 'department':None, 'team':None,
                          'audience_roles':[], 'audience_user_ids':[], 'audience_position_ids':[], 'audience_branch_ids':[], 'entry_visibility':'STANDARD', 'share_confidential':False},
                    fields=validated_fields)
            else:
                target = FormTemplateVersionService.create_draft(
                    company=request.user.company, actor=request.user,
                    data={'code':code, 'starter_code':code, 'name':starter.name, 'description':starter.description,
                          'category':starter.category, 'allow_drafts':True}, fields=validated_fields)
            created.append(target)
        return Response({'created':self.get_serializer(created, many=True).data,
                         'existing':self.get_serializer(existing, many=True).data}, status=201 if created else 200)


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
        CanUseFormSubmissions,
    ]

    def get_permissions(self):
        if self.action == 'approve_materials':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='my-work')
    def my_work(self, request):
        """Personal dashboard counts, never colleagues' entries or answers."""
        from django.db.models import Count, Case, When, Value, IntegerField
        own = self.get_queryset().filter(submitted_by=request.user)
        counts = dict(own.order_by().values('status').annotate(total=Count('pk', distinct=True))
                      .values_list('status', 'total'))
        recent = own.select_related('template').annotate(work_priority=Case(
            When(status='RETURNED', then=Value(0)),
            When(status='DRAFT', then=Value(1)),
            default=Value(2), output_field=IntegerField(),
        )).order_by('work_priority', '-updated_at', '-pk')[:5]
        return Response({
            'counts': {key: counts.get(key, 0) for key, _ in FormSubmission.STATUS_CHOICES},
            'recent': [{'id': str(row.pk), 'name': row.template.name,
                        'status': row.status, 'updated_at': row.updated_at}
                       for row in recent],
        })

    @extend_schema(operation_id='materials_workspace_list')
    @action(detail=False, methods=['get'], url_path='materials')
    def materials_list(self, request):
        from .materials import representation
        objects=self.get_queryset().filter(material_journey__isnull=False).select_related('material_journey').order_by('-created_at')
        page=self.paginate_queryset(objects)
        data=[{'id':str(obj.pk),'title':obj.title or obj.template.name,**representation(obj.material_journey,request.user)} for obj in (page if page is not None else objects[:100])]
        return self.get_paginated_response(data) if page is not None else Response(data)

    @action(detail=True, methods=['get','post'], url_path='materials')
    def materials(self, request, pk=None):
        from .materials import representation, move
        from .models import MaterialJourney
        from rest_framework import serializers
        submission=self.get_object()
        journey=MaterialJourney.objects.filter(submission=submission).first()
        if not journey: raise ValidationError('This submission is not a connected material request.')
        if request.method=='GET': return Response(representation(journey,request.user))
        class Movement(serializers.Serializer):
            stage=serializers.ChoiceField(choices=['DISPATCH','RECEIPT','RETURN'])
            template_id=serializers.UUIDField()
            quantities=serializers.DictField(child=serializers.DecimalField(max_digits=19,decimal_places=6,min_value=0))
            reference=serializers.UUIDField()
            related_reference=serializers.UUIDField(required=False,allow_null=True)
            note=serializers.CharField(max_length=4000,required=False,allow_blank=True)
            answers=serializers.JSONField(required=False)
        values=Movement(data=request.data);values.is_valid(raise_exception=True)
        return Response(move(submission=submission,actor=request.user,**values.validated_data))

    @action(detail=True, methods=['post'], url_path='approve-materials')
    @transaction.atomic
    def approve_materials(self, request, pk=None):
        from .materials import number, representation
        from .models import MaterialJourney
        from workflows.runtime_service import WorkflowRuntimeService
        from workflows.services import WorkflowService
        from rest_framework import serializers
        submission=self.get_object()
        instance=WorkflowInstance.objects.select_for_update().filter(company=request.user.company,object_id=str(submission.pk),content_type=ContentType.objects.get_for_model(FormSubmission),status='IN_PROGRESS').order_by('-started_at','-pk').first()
        if not instance: raise ValidationError('No active review is available.')
        step=instance.steps.filter(status='PENDING').order_by('order').first()
        if not step or instance.steps.filter(order__gt=step.order,status='WAITING').exists():
            raise ValidationError('Quantity approval belongs to the final review stage.')
        WorkflowService._recipient_for_user(step,request.user,permission='REVIEW_SUBMISSIONS')
        class Quantities(serializers.Serializer):
            quantities=serializers.DictField(child=serializers.DecimalField(max_digits=19,decimal_places=6,min_value=0))
            note=serializers.CharField(max_length=4000,required=False,allow_blank=True,default='')
        values=Quantities(data=request.data);values.is_valid(raise_exception=True)
        journey=MaterialJourney.objects.select_for_update().get(submission=submission)
        amounts=values.validated_data['quantities']
        if set(amounts)!={item['id'] for item in journey.items} or any(number(amounts[item['id']])>number(item['quantity']) for item in journey.items) or not any(amounts.values()):
            raise ValidationError('Choose approved quantities for every item, within the requested amounts. Reject the request if no items are approved.')
        normalized={key:str(value) for key,value in amounts.items()}
        if journey.approved and any(number(journey.approved[key]) != number(value) for key,value in normalized.items()):
            raise ValidationError('Another reviewer has already recorded different quantities. Return the request for correction instead.')
        journey.approved=normalized;journey.save(update_fields=['approved'])
        WorkflowRuntimeService.approve(instance=instance,actor=request.user,note=values.validated_data['note'],request=request)
        journey.submission.refresh_from_db()
        return Response(representation(journey,request.user))

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

        visible = VisibilityService.form_submissions_queryset(
            user=user,
            queryset=queryset,
        )
        if self.action == 'list':
            status = self.request.query_params.get('status', '')
            if status:
                if status not in dict(FormSubmission.STATUS_CHOICES):
                    raise ValidationError({'status': 'Choose an entry status.'})
                visible = visible.filter(status=status)
            search = self.request.query_params.get('search', '').strip()[:200]
            if search:
                visible = visible.filter(Q(title__icontains=search) | Q(template__name__icontains=search) | Q(reference_number__icontains=search))
        return visible

    @action(detail=True, methods=['get', 'post'])
    def attachments(self, request, pk=None):
        from django.db import transaction
        from documents.services import AttachmentService
        from .attachments import can_read_files, can_edit_files, can_upload_files
        from rest_framework.exceptions import PermissionDenied
        with transaction.atomic():
            submission = self.get_object()
            submission = FormSubmission.objects.select_for_update().get(pk=submission.pk)
            if request.method == 'POST':
                if not can_upload_files(request.user, submission):
                    raise PermissionDenied('Attachments are locked for this submission.')
                uploaded = request.FILES.get('file')
                if not uploaded:
                    raise ValidationError({'file': 'Choose a file to upload.'})
                attachment = AttachmentService.create(actor=request.user, parent=submission, file=uploaded,
                    original_filename=uploaded.name, mime_type='', file_size=uploaded.size)
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
