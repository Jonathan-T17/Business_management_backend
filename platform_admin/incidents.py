from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService
from security.services import create_audit_log
from .models import SecurityIncident, IncidentEvent
from .permissions import RequiresPlatformCapability
from .maintenance import MaintenanceWriteThrottle


class IncidentPermission(RequiresPlatformCapability):
    def has_permission(self, request, view):
        self.capability = C.VIEW_PLATFORM_AUDIT if request.method in ("GET", "HEAD", "OPTIONS") else C.MANAGE_PLATFORM_SECURITY
        return super().has_permission(request, view)


class IncidentEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True)
    class Meta:
        model = IncidentEvent
        fields = ("id", "actor_name", "status", "note", "created_at")
        read_only_fields = fields


class IncidentSerializer(serializers.ModelSerializer):
    events = IncidentEventSerializer(many=True, read_only=True)
    company_name = serializers.CharField(source="company.name", default=None, read_only=True)
    assigned_name = serializers.CharField(source="assigned_to.full_name", default=None, read_only=True)
    class Meta:
        model = SecurityIncident
        fields = ("id", "title", "severity", "status", "company", "company_name", "assigned_to", "assigned_name", "created_at", "updated_at", "resolved_at", "events")
        read_only_fields = fields


class IncidentCreate(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    severity = serializers.ChoiceField(choices=("INFO", "WARNING", "CRITICAL"), default="WARNING")
    note = serializers.CharField(max_length=2000)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class IncidentUpdate(serializers.Serializer):
    status = serializers.ChoiceField(choices=("OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"))
    note = serializers.CharField(max_length=2000)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)
    updated_at = serializers.DateTimeField()


class IncidentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IncidentPermission,)
    throttle_classes = (MaintenanceWriteThrottle,)
    serializer_class = IncidentSerializer
    queryset = SecurityIncident.objects.select_related("company", "assigned_to").prefetch_related("events__actor")

    def checked(self, request, serializer_type):
        serializer = serializer_type(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        if not request.user.check_password(values.pop("password")):
            raise ValidationError({"password": "Your password could not be verified."})
        return values

    @transaction.atomic
    @extend_schema(request=IncidentCreate, responses={201: IncidentSerializer})
    def create(self, request):
        values = self.checked(request, IncidentCreate)
        note = values.pop("note")
        incident = SecurityIncident.objects.create(created_by=request.user, assigned_to=request.user, **values)
        IncidentEvent.objects.create(incident=incident, actor=request.user, status=incident.status, note=note)
        create_audit_log(user=request.user, request=request, action="SECURITY_INCIDENT_CREATED", severity=incident.severity,
                         obj=incident, description="Security incident created.")
        return Response(IncidentSerializer(incident).data, status=201)

    @extend_schema(request=IncidentUpdate, responses=IncidentSerializer)
    @action(detail=True, methods=("post",))
    @transaction.atomic
    def transition(self, request, pk=None):
        values = self.checked(request, IncidentUpdate)
        incident = SecurityIncident.objects.select_for_update().get(pk=self.get_object().pk)
        if incident.updated_at != values["updated_at"]:
            raise ValidationError("This incident changed. Refresh before saving.")
        allowed = {"OPEN": {"INVESTIGATING", "RESOLVED"}, "INVESTIGATING": {"CONTAINED", "RESOLVED"},
                   "CONTAINED": {"INVESTIGATING", "RESOLVED"}, "RESOLVED": {"INVESTIGATING"}}
        if values["status"] not in allowed[incident.status]:
            raise ValidationError("This status change is not available.")
        incident.status = values["status"]
        incident.resolved_at = timezone.now() if incident.status == "RESOLVED" else None
        incident.save(update_fields=("status", "resolved_at", "updated_at"))
        IncidentEvent.objects.create(incident=incident, actor=request.user, status=incident.status, note=values["note"])
        create_audit_log(user=request.user, request=request, action="SECURITY_INCIDENT_UPDATED", severity="WARNING",
                         obj=incident, description="Security incident status changed.", metadata={"status": incident.status})
        return Response(IncidentSerializer(incident).data)
