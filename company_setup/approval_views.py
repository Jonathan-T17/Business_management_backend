"""Tenant approval configuration with explicit recipient validation."""
import uuid
from django.db import transaction, IntegrityError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from workflows.models import WorkflowDefinition, WorkflowStepDefinition
from organizations.models import Position
from users.models import User
from .models import ApprovalRoute
from .configuration_views import CompanyConfigurationViewSet


class RecipientInput(serializers.Serializer):
    type = serializers.ChoiceField(choices=WorkflowStepDefinition.RECIPIENT_TYPES)
    position_id = serializers.IntegerField(required=False)
    user_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(choices=['ADMIN', 'MANAGER', 'EMPLOYEE', 'INDIVIDUAL'], required=False)

    def validate(self, attrs):
        company = self.context['request'].user.company
        kind = attrs['type']
        expected = {'POSITION': 'position_id', 'USER': 'user_id', 'ROLE': 'role'}.get(kind)
        if expected and expected not in attrs:
            raise serializers.ValidationError({expected: 'Select a reviewer.'})
        if set(attrs) - {'type', expected}:
            raise serializers.ValidationError('Remove recipient fields that do not match the selected reviewer type.')
        if kind == 'POSITION' and not Position.objects.filter(pk=attrs['position_id'], company=company, is_active=True).exists():
            raise serializers.ValidationError('Choose an active position in your company.')
        if kind == 'USER' and not User.objects.filter(pk=attrs['user_id'], company=company, is_active=True, is_deleted=False, is_superuser=False).exclude(role='SUPERUSER').exists():
            raise serializers.ValidationError('Choose an active company user.')
        return attrs


class StepInput(serializers.Serializer):
    order = serializers.IntegerField(min_value=1)
    label = serializers.CharField(max_length=255)
    recipient = RecipientInput()
    approval_mode = serializers.ChoiceField(choices=WorkflowStepDefinition.APPROVAL_MODES, default='ANY')
    can_return = serializers.BooleanField(default=True)
    can_reject = serializers.BooleanField(default=True)
    notify_in_app = serializers.BooleanField(default=True)
    notify_email = serializers.BooleanField(default=False)


class RouteInput(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    steps = StepInput(many=True, allow_empty=False)

    def validate_steps(self, steps):
        validator = StepInput(data=steps, many=True, context=self.context)
        validator.is_valid(raise_exception=True)
        steps = validator.validated_data
        if len(steps) > 30:
            raise serializers.ValidationError('Use at most 30 review steps.')
        if sorted(step['order'] for step in steps) != list(range(1, len(steps) + 1)):
            raise serializers.ValidationError('Step order must be consecutive, starting at 1.')
        return sorted(steps, key=lambda step: step['order'])


class RouteOutput(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField()
    steps_editable = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRoute
        fields = ['id', 'name', 'description', 'is_active', 'workflow', 'steps', 'steps_editable']

    def get_steps_editable(self, obj):
        return not obj.workflow.instances.exists()

    def get_steps(self, obj):
        return [{'order': step.order, 'label': step.name,
                 'recipient': {k:v for k,v in {'type':step.recipient_type,
                    'position_id':str(step.recipient_position_id) if step.recipient_position_id else None,
                    'user_id':str(step.recipient_user_id) if step.recipient_user_id else None,
                    'role':step.recipient_role or None}.items() if v is not None},
                 'can_return':step.can_return, 'can_reject':step.can_reject,
                 'approval_mode':step.approval_mode, 'notify_email':step.notify_email,
                 'notify_in_app':step.notify_in_app} for step in obj.workflow.steps.all()]


class ApprovalRouteViewSet(CompanyConfigurationViewSet):
    queryset = ApprovalRoute.objects.select_related('workflow').prefetch_related('workflow__steps')
    serializer_class = RouteOutput

    @action(detail=False, methods=['post'])
    def preview(self, request):
        payload = RouteInput(data=request.data, context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        return Response({'valid':True, 'steps':payload.validated_data['steps'],
                         'message':'Configuration is valid. Actual reviewers are resolved when work is submitted.'})

    def create(self, request, *args, **kwargs):
        return self.save_route(request)

    def update(self, request, *args, **kwargs):
        return self.save_route(request, instance=self.get_object(), partial=kwargs.get('partial', False))

    @transaction.atomic
    def save_route(self, request, instance=None, partial=False):
        payload = RouteInput(data=request.data, partial=partial, context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        if instance:
            instance = ApprovalRoute.objects.select_for_update().get(pk=instance.pk, company=request.user.company)
            workflow = WorkflowDefinition.objects.select_for_update().get(pk=instance.workflow_id)
            if workflow.form_templates.exclude(lifecycle_status='DRAFT').exists():
                raise serializers.ValidationError('This route is pinned to a published form. Create a new route.')
            if 'steps' in data and workflow.instances.exists():
                raise serializers.ValidationError({'steps':'This route has approval history. Create a new route to change its steps.'})
        else:
            workflow = WorkflowDefinition.objects.create(company=request.user.company, name=data['name'],
                code='approval-'+uuid.uuid4().hex, target_type='FORM_SUBMISSION', created_by=request.user)
            instance = ApprovalRoute(company=request.user.company, workflow=workflow)
        creating = instance.pk is None
        for field in ('name', 'description', 'is_active'):
            if field in data:
                setattr(instance, field, data[field])
                setattr(workflow, field, data[field])
        try:
            with transaction.atomic():
                instance.save()
                workflow.save()
        except IntegrityError:
            raise serializers.ValidationError({'name':'An approval route with this name already exists.'})
        if 'steps' in data:
            workflow.steps.all().delete()
            for step in data['steps']:
                recipient = step['recipient']
                WorkflowStepDefinition.objects.create(workflow=workflow, name=step['label'], order=step['order'],
                    recipient_type=recipient['type'], recipient_user_id=recipient.get('user_id'),
                    recipient_position_id=recipient.get('position_id'), recipient_role=recipient.get('role',''),
                    **{key:step[key] for key in ('approval_mode','can_return','can_reject','notify_in_app','notify_email')})
        self.audit(instance, 'CREATE' if creating else 'UPDATE')
        return Response(RouteOutput(instance).data, status=201 if creating else 200)
