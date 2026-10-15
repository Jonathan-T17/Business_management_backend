from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from security.models import ActiveSession, FailedLoginAttempt, AuditLog
from .models import SecurityIncident
from security.services import current_sessions
from .permissions import CanViewPlatformSecurity


class SecuritySummaryView(APIView):
    permission_classes = (CanViewPlatformSecurity,)

    @extend_schema(responses=inline_serializer(name="PlatformSecuritySummary", fields={
        "security": inline_serializer(name="SecuritySummaryCounts", fields={key: serializers.IntegerField() for key in
             ("active_sessions", "failed_logins_24h", "locked_records", "critical_events_24h")}),
        "open_incidents": serializers.IntegerField(), "authentication": serializers.CharField(),
    }))
    def get(self, request):
        now = timezone.now()
        return Response({"security": {
            "active_sessions": current_sessions().count(),
            "failed_logins_24h": FailedLoginAttempt.objects.filter(last_attempt_at__gte=now-timedelta(days=1)).count(),
            "locked_records": FailedLoginAttempt.objects.filter(locked_until__gt=now).count(),
            "critical_events_24h": AuditLog.objects.filter(severity="CRITICAL", created_at__gte=now-timedelta(days=1)).count(),
        }, "open_incidents": SecurityIncident.objects.exclude(status="RESOLVED").count(),
           "authentication": "Every administrator sign-in requires a password plus email verification or a registered, device-verified passkey. Email recovery remains available."})
