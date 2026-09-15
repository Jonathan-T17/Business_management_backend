"""Explicit, audited maintenance resources for the platform frontend.

Never expose arbitrary Django models or auto-enable new model fields here.
Lifecycle and security actions continue to use their dedicated endpoints.
"""
from django.apps import apps
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction, IntegrityError
from django.db.models import Q
from django.forms import modelform_factory
from rest_framework.generics import get_object_or_404
from django.utils.crypto import salted_hmac, constant_time_compare
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from security.services import create_audit_log, terminate_user_sessions
import json


# Each field is deliberately reviewed. Credentials and immutable evidence are absent.
RESOURCES = {
    'form-starters': ('forms_engine.FormStarter', 'Starter form designs', 'Product designs only; no company submissions or assignments',
        'code name description category field_schema is_active', True),
    'companies': ('companies.Company', 'Companies', 'Company profile and communication settings',
        'name official_name registration_number slug description website email phone address country timezone default_currency date_format week_starts_on email_from_name email_reply_to email_footer email_notifications_enabled', True),
    'branches': ('companies.Branch', 'Branches', 'Company branches and their managers',
        'company name code location manager is_active', True),
    'users': ('users.User', 'User profiles', 'Account details and roles; lifecycle actions remain on Users',
        'email full_name phone_number user_timezone preferred_language role branch', False),
    'projects': ('projects.Project', 'Projects', 'Project configuration',
        'company name description is_active', True),
    'project-memberships': ('projects.ProjectMembership', 'Project memberships', 'Project access and roles',
        'project user role', True),
    'plans': ('subscriptions.Plan', 'Subscription plans', 'Prices, capacity and feature availability',
        'name max_users max_projects max_branches storage_limit_bytes ai_analytics_enabled reports_enabled field_operations_enabled advanced_workflows_enabled official_records_enabled custom_forms_enabled price_monthly is_active', True),
    'subscriptions': ('subscriptions.Subscription', 'Subscription records', 'Company plan, expiry and subscription status',
        'company plan is_active expires_at', True),

}


class MaintenancePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_superuser
                    and user.is_staff and not user.is_deleted and not user.must_change_password)


class MaintenanceWriteThrottle(UserRateThrottle):
    scope = 'maintenance_write'
    rate = '10/min'

    def allow_request(self, request, view):
        return True if request.method in ('GET', 'HEAD', 'OPTIONS') else super().allow_request(request, view)


class ChangeEnvelope(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)
    values = serializers.DictField()
    version = serializers.CharField(required=False)


def resource(key):
    if key not in RESOURCES:
        from rest_framework.exceptions import NotFound
        raise NotFound('Administration resource not found.')
    label, title, description, names, can_create = RESOURCES[key]
    return apps.get_model(label), title, description, names.split(), can_create


def tenant_id(obj):
    if obj is None:
        return None
    if obj._meta.label == 'companies.Company':
        return obj.pk
    if hasattr(obj, 'company_id'):
        return obj.company_id
    for field in ('project', 'template'):
        if hasattr(obj, field):
            return tenant_id(getattr(obj, field))
    return None


def values_for(obj, names):
    result = {}
    for name in names:
        field = obj._meta.get_field(name)
        value = getattr(obj, field.attname)
        if isinstance(value, (dict, list, bool, int, float)) or value is None:
            result[name] = value
        else:
            result[name] = str(value)
    return result


def version_for(obj, names):
    data = json.dumps(values_for(obj, names), sort_keys=True)
    return salted_hmac('platform-maintenance', data).hexdigest()


def record(obj, names):
    return {'id': str(obj.pk), 'label': str(obj), 'values': values_for(obj, names),
            'version': version_for(obj, names), 'company': str(tenant_id(obj) or '')}


def describe_fields(model, names):
    fields = []
    for name in names:
        f = model._meta.get_field(name)
        kind = 'text'
        if f.is_relation:
            kind = 'relation'
        elif f.choices:
            kind = 'choice'
        elif isinstance(f, models.BooleanField):
            kind = 'boolean'
        elif isinstance(f, models.JSONField):
            kind = 'json'
        elif isinstance(f, models.DateTimeField):
            kind = 'datetime-local'
        elif isinstance(f, models.DateField):
            kind = 'date'
        elif isinstance(f, (models.IntegerField, models.DecimalField, models.FloatField)):
            kind = 'number'
        elif isinstance(f, models.TextField):
            kind = 'textarea'
        elif isinstance(f, models.EmailField):
            kind = 'email'
        fields.append({'name': name, 'label': str(f.verbose_name).capitalize(), 'kind': kind,
                       'required': not f.blank and not f.null, 'nullable': f.null,
                       'choices': [{'value': str(v), 'label': str(label)} for v, label in f.flatchoices],
                       'default': f.get_default() if f.has_default() else (False if kind == 'boolean' else ''),
                       'max_length': f.max_length})
    return fields


def validate_boundaries(key, obj, previous):
    company_id = tenant_id(obj)
    if previous and tenant_id(previous) != company_id:
        raise ValidationError('Existing records cannot be transferred between companies here.')
    for field in obj._meta.fields:
        if not field.is_relation or field.name in ('created_by', 'added_by'):
            continue
        related = getattr(obj, field.name, None)
        if related is not None and field.name != 'company' and hasattr(related, 'company_id'):
            if related.company_id != company_id:
                raise ValidationError({field.name: 'Select a record belonging to the same company.'})
    if key == 'users':
        from core.authorization import Authorization
        from users.services import TenantUserLifecycleService
        if previous and previous.role != obj.role and (Authorization.is_platform_superuser(previous) or obj.role == 'SUPERUSER'):
            raise ValidationError('Platform role changes require the dedicated platform account workflow.')
        if previous and previous.role == 'ADMIN' and obj.role != 'ADMIN':
            TenantUserLifecycleService._guard_last_admin(previous, 'demote')
    if key in ('form-templates', 'form-fields'):
        template = obj if key == 'form-templates' else obj.template
        previous_template = (previous if key == 'form-templates' else previous.template) if previous else None
        if template.lifecycle_status != 'DRAFT' or (previous_template and previous_template.lifecycle_status != 'DRAFT'):
            raise ValidationError('Create a new draft version before changing a published or archived template.')
    if key in ('plans', 'subscriptions'):
        from subscriptions.models import Subscription
        if key == 'plans' and obj.price_monthly < 0:
            raise ValidationError({'price_monthly': 'The price cannot be negative.'})
        subscriptions = (Subscription.objects.filter(plan=obj) if obj.pk else []) if key == 'plans' else [obj]
        for subscription in subscriptions:
            company = subscription.company
            plan = obj if key == 'plans' else subscription.plan
            from subscriptions.services import SubscriptionCapacity
            SubscriptionCapacity.validate(company, plan)
            if key == 'subscriptions' and obj.is_active and not plan.is_active:
                raise ValidationError('Choose an active plan before activating a subscription.')


class MaintenanceCatalogue(APIView):
    permission_classes = [MaintenancePermission]

    def get(self, request):
        return Response([{'key': key, 'title': value[1], 'description': value[2], 'can_create': value[4]}
                         for key, value in RESOURCES.items()])


class MaintenanceRecords(APIView):
    permission_classes = [MaintenancePermission]
    throttle_classes = [MaintenanceWriteThrottle]

    def get(self, request, key, pk=None):
        model, title, description, names, can_create = resource(key)
        if pk is not None:
            obj = get_object_or_404(model, pk=pk)
            return Response(record(obj, names))
        queryset = model.objects.all().order_by('pk')
        search = request.query_params.get('search', '').strip()[:100]
        if search:
            query = Q()
            for name in names:
                if isinstance(model._meta.get_field(name), (models.CharField, models.TextField)):
                    query |= Q(**{name + '__icontains': search})
            if query:
                queryset = queryset.filter(query)
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            raise ValidationError('Invalid page number.')
        return Response({'title': title, 'description': description, 'fields': describe_fields(model, names),
                         'can_create': can_create, 'count': queryset.count(), 'page': page,
                         'results': [record(obj, names) for obj in queryset[(page-1)*20:page*20]]})

    def post(self, request, key, pk=None):
        return self.save(request, key, pk)

    def put(self, request, key, pk):
        return self.save(request, key, pk)

    @transaction.atomic
    def save(self, request, key, pk):
        model, title, description, names, can_create = resource(key)
        envelope = ChangeEnvelope(data=request.data)
        envelope.is_valid(raise_exception=True)
        data = envelope.validated_data
        # Lock the actor so concurrent privilege changes cannot authorize a stale write.
        actor = type(request.user).objects.select_for_update().get(pk=request.user.pk)
        if not actor.is_active or not actor.is_superuser or not actor.is_staff or actor.is_deleted:
            raise PermissionDenied()
        if not actor.check_password(data['password']):
            raise ValidationError({'password': 'Your password could not be verified.'})
        if pk is None and not can_create:
            raise ValidationError('Use the dedicated account creation workflow.')
        if set(data['values']) - set(names):
            raise ValidationError('The request contains fields that cannot be edited here.')
        obj = get_object_or_404(model.objects.select_for_update(), pk=pk) if pk else None
        if obj and not constant_time_compare(data.get('version', ''), version_for(obj, names)):
            raise ValidationError('This record has changed. Reopen it before saving.')
        # Serialize edits within a company to protect last-admin and relation checks.
        if obj and tenant_id(obj):
            apps.get_model('companies.Company').objects.select_for_update().get(pk=tenant_id(obj))
        previous = model.objects.get(pk=pk) if pk else None
        form_class = modelform_factory(model, fields=names)
        form = form_class(data=data['values'], instance=obj)
        if not form.is_valid():
            raise ValidationError(dict(form.errors))
        obj = form.save(commit=False)
        validate_boundaries(key, obj, previous)
        for attr in ('created_by', 'added_by'):
            if previous is None and hasattr(obj, attr + '_id'):
                setattr(obj, attr, actor)
        try:
            with transaction.atomic():
                obj.save()
                form.save_m2m()
        except IntegrityError:
            raise ValidationError('The record conflicts with an existing record. Refresh and try again.')
        if key == 'users' and previous and previous.role != obj.role:
            terminate_user_sessions(obj, reason='Platform administrator changed account role')
        changed = [name for name in names if previous is None or values_for(previous, names)[name] != values_for(obj, names)[name]]
        create_audit_log(user=actor, request=request, company=getattr(obj, 'company', None), obj=obj,
                         action='PLATFORM_RECORD_CREATED' if previous is None else 'PLATFORM_RECORD_UPDATED',
                         description=data['reason'], severity='WARNING',
                         metadata={'resource': key, 'changed_fields': changed})
        return Response(record(obj, names), status=201 if previous is None else 200)


class MaintenanceChoices(APIView):
    permission_classes = [MaintenancePermission]

    def get(self, request, key, field):
        model, _, _, names, _ = resource(key)
        if field not in names or not model._meta.get_field(field).is_relation:
            raise ValidationError('Unknown relationship.')
        related_model = model._meta.get_field(field).related_model
        queryset = related_model.objects.all().order_by('pk')
        company = request.query_params.get('company')
        if company and any(f.name == 'company' for f in related_model._meta.fields):
            try:
                queryset = queryset.filter(company_id=company)
            except (ValueError, DjangoValidationError):
                raise ValidationError('Invalid company.')
        search = request.query_params.get('search', '').strip()[:100]
        if search:
            query = Q()
            for name in ('name', 'full_name', 'email', 'code'):
                if any(f.name == name for f in related_model._meta.fields):
                    query |= Q(**{name + '__icontains': search})
            if query:
                queryset = queryset.filter(query)
        selected = request.query_params.get('selected')
        rows = list(queryset[:40])
        if selected:
            try:
                current = related_model.objects.filter(pk=selected).first()
            except (ValueError, DjangoValidationError):
                current = None
            if current and current not in rows:
                rows.insert(0, current)
        choices = []
        for obj in rows:
            choice = {'value': str(obj.pk), 'label': str(obj)}
            if key == 'subscriptions' and field == 'plan' and company:
                from subscriptions.services import SubscriptionCapacity
                owner = get_object_or_404(apps.get_model('companies.Company'), pk=company)
                choice['issues'] = SubscriptionCapacity.issues(owner, obj)
                if not obj.is_active:
                    choice['issues'].append('This plan is inactive.')
                choice['label'] += f" — {obj.max_users} people / {obj.max_projects} projects / {obj.max_branches} branches"
            choices.append(choice)
        return Response(choices)
