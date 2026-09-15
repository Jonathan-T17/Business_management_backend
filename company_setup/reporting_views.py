"""Atomic composition of a draft form and its reporting schedule."""
import uuid
from django.db import transaction, IntegrityError
from reporting_schedules.services import ReportingScheduleService
from rest_framework import serializers
from rest_framework.response import Response
from organizations.models import Position
from forms_engine.models import FormTemplate, FormField
from reporting_schedules.models import ReportingSchedule
from workflows.models import WorkflowDefinition, WorkflowStepDefinition
from .models import ReportingProcess, ApprovalRoute
from .approval_views import StepInput, RouteOutput
from .configuration_views import CompanyConfigurationViewSet

class SubmittersInput(serializers.Serializer):
    type = serializers.ChoiceField(choices=['POSITION'])
    position_id = serializers.IntegerField()

    def validate_position_id(self, value):
        if not Position.objects.filter(pk=value, company=self.context['request'].user.company, is_active=True).exists():
            raise serializers.ValidationError('Choose an active position in your company.')
        return value

class ScheduleInput(serializers.Serializer):
    frequency = serializers.ChoiceField(choices=['DAILY','WEEKLY','MONTHLY'])
    due_time = serializers.TimeField()
    weekday = serializers.IntegerField(min_value=0, max_value=6, required=False, allow_null=True)
    day_of_month = serializers.IntegerField(min_value=1, max_value=28, required=False, allow_null=True)

    def validate(self, attrs):
        if self.root.partial:
            return attrs
        if attrs.get('frequency') == 'WEEKLY' and attrs.get('weekday') is None:
            raise serializers.ValidationError({'weekday':'Choose the reporting weekday.'})
        if attrs.get('frequency') == 'MONTHLY' and attrs.get('day_of_month') is None:
            raise serializers.ValidationError({'day_of_month':'Choose a day between 1 and 28, available every month.'})
        return attrs

class FieldInput(serializers.Serializer):
    key = serializers.SlugField(max_length=100)
    label = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=['TEXT','LONG_TEXT','INTEGER','DECIMAL','BOOLEAN','DATE','TIME','DATETIME','EMAIL','PHONE'])
    required = serializers.BooleanField(default=False)

class ProcessInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True)
    submitters = SubmittersInput()
    schedule = ScheduleInput()
    fields = FieldInput(many=True, allow_empty=False)
    approval_route = StepInput(many=True, required=False, default=list)
    is_active = serializers.BooleanField(required=False)

    def validate_fields(self, value):
        if len(value) > 100 or len({item['key'] for item in value}) != len(value):
            raise serializers.ValidationError('Use unique field keys and at most 100 fields.')
        return value

    def validate_approval_route(self, value):
        if len(value) > 30 or sorted(item['order'] for item in value) != list(range(1,len(value)+1)):
            raise serializers.ValidationError('Use consecutive approval steps starting at 1, with at most 30 steps.')
        return value

class ProcessOutput(serializers.ModelSerializer):
    schedule = serializers.SerializerMethodField()
    submitters = serializers.SerializerMethodField()
    fields = serializers.SerializerMethodField(method_name='get_form_fields')
    approval_route = serializers.SerializerMethodField()
    template = serializers.UUIDField(source='schedule.template_id')
    template_status = serializers.CharField(source='schedule.template.lifecycle_status')

    class Meta:
        model = ReportingProcess
        fields = ['id','name','description','schedule','submitters','fields','approval_route','is_active','template','template_status']

    def get_schedule(self, obj):
        schedule = obj.schedule
        return {'frequency':schedule.frequency,'due_time':str(schedule.due_time or ''),'weekday':schedule.weekday,'day_of_month':schedule.day_of_month}
    def get_submitters(self, obj):
        return {'type':obj.schedule.target_type,'position_id':str(obj.schedule.target_position_id or '')}
    def get_form_fields(self, obj):
        return [{'key':f.key,'label':f.label,'type':f.field_type,'required':f.required} for f in obj.schedule.template.fields.all()]
    def get_approval_route(self, obj):
        return RouteOutput(obj.approval_route).data['steps'] if obj.approval_route else []

class ReportingProcessViewSet(CompanyConfigurationViewSet):
    queryset = ReportingProcess.objects.select_related('schedule__template','approval_route__workflow')
    serializer_class = ProcessOutput

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        payload = ProcessInput(data=request.data, context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if data.get('is_active'):
            raise serializers.ValidationError('Review and publish the draft form before activation.')
        company = request.user.company
        if ReportingProcess.objects.filter(company=company,name=data['name']).exists():
            raise serializers.ValidationError({'name':'A reporting process with this name already exists.'})
        code = uuid.uuid4().hex
        route = None
        if data['approval_route']:
            workflow = WorkflowDefinition.objects.create(company=company,name=data['name'],code='report-'+code,target_type='FORM_SUBMISSION',created_by=request.user)
            for step in data['approval_route']:
                recipient = step['recipient']
                WorkflowStepDefinition.objects.create(workflow=workflow,name=step['label'],order=step['order'],recipient_type=recipient['type'],recipient_position_id=recipient.get('position_id'),recipient_user_id=recipient.get('user_id'),recipient_role=recipient.get('role',''),**{key:step[key] for key in ('approval_mode','can_return','can_reject','notify_in_app','notify_email')})
            route = ApprovalRoute.objects.create(company=company,name='Reporting '+code,description=data['name'],workflow=workflow)
        template = FormTemplate.objects.create(company=company,name=data['name'],code='report-'+code,description=data.get('description',''),category='CUSTOM',workflow=route.workflow if route else None,created_by=request.user,lifecycle_status='DRAFT')
        for order, field in enumerate(data['fields']):
            FormField.objects.create(template=template,key=field['key'],label=field['label'],field_type=field['type'],required=field['required'],order=order)
        schedule = ReportingSchedule.objects.create(company=company,name=data['name'],template=template,target_type='POSITION',target_position_id=data['submitters']['position_id'],start_date=ReportingScheduleService.local_date(company),is_active=False,created_by=request.user,**data['schedule'])
        try:
            with transaction.atomic():
                process = ReportingProcess.objects.create(company=company,name=data['name'],description=data.get('description',''),schedule=schedule,approval_route=route,is_active=False)
        except IntegrityError:
            raise serializers.ValidationError({'name':'A reporting process with this name already exists.'})
        self.audit(process,'CREATE')
        return Response(ProcessOutput(process).data,status=201)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        process = self.get_object()
        process = ReportingProcess.objects.select_for_update().get(pk=process.pk)
        if not isinstance(request.data, dict) or set(request.data) - {'name','description','is_active','schedule'}:
            raise serializers.ValidationError('Edit form fields through the form editor and reviewers through approval routes.')
        payload = ProcessInput(data=request.data,partial=True,context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        schedule = ReportingSchedule.objects.select_for_update().get(pk=process.schedule_id)
        if data.get('is_active') and (schedule.template.lifecycle_status != 'PUBLISHED' or not schedule.template.is_active):
            raise serializers.ValidationError('Publish an active form before activating reporting.')
        if 'schedule' in data:
            merged = {key:getattr(schedule,key) for key in ('frequency','due_time','weekday','day_of_month')}
            merged.update(data['schedule'])
            check = ScheduleInput(data=merged)
            check.is_valid(raise_exception=True)
            for key,value in check.validated_data.items():
                setattr(schedule,key,value)
        for key in ('name','description','is_active'):
            if key in data:
                setattr(process,key,data[key]); setattr(schedule,key,data[key])
        try:
            with transaction.atomic():
                process.save(); schedule.save()
        except IntegrityError:
            raise serializers.ValidationError({'name':'A reporting process with this name already exists.'})
        self.audit(process,'UPDATE')
        return Response(ProcessOutput(process).data)
