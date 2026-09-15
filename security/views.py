from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ActiveSession, TrustedDevice, AuditLog, LoginHistory
from .serializers import ActiveSessionSerializer, CompanyAuditLogSerializer, TrustedDeviceSerializer, AuditLogSerializer, LoginHistorySerializer
from security.services import create_audit_log, terminate_session
from companies.permissions import IsCompanyAdmin
from users.permissions import IsSuperUserOrPlatformAdmin


# User-level viewset
class TrustedDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = TrustedDeviceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed("POST", "Devices are trusted through verified login.")

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        return self.destroy(request, pk=pk)

    def get_queryset(self):
        return TrustedDevice.objects.filter(user=self.request.user, is_active=True)

    def destroy(self, request, *args, **kwargs):
        device = self.get_object()
        device.is_active = False
        device.revoked_at = timezone.now()
        device.revoked_by = request.user
        device.save(update_fields=["is_active", "revoked_at", "revoked_by"])

        create_audit_log(
            user=request.user,
            action="SECURITY",
            request=request,
            description=f"Trusted device revoked: {device.device_name}",
        )

        return Response({"message": "Device revoked successfully"}, status=status.HTTP_200_OK)


# Platform admin viewsets
class MySessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActiveSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActiveSession.objects.filter(user=self.request.user, is_active=True).order_by("-last_activity")

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        session = self.get_object()
        terminate_session(session=session, actor=request.user, reason="SECURITY", request=request)
        return Response({"message": "Session revoked."})


class TrustedDeviceAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrustedDeviceSerializer
    permission_classes = [IsSuperUserOrPlatformAdmin]

    def get_queryset(self):
        return TrustedDevice.objects.all()


class AuditLogAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsSuperUserOrPlatformAdmin]

    def get_queryset(self):
        return AuditLog.objects.all().order_by("-created_at")


class LoginHistoryAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoginHistorySerializer
    permission_classes = [IsSuperUserOrPlatformAdmin]

    def get_queryset(self):
        return LoginHistory.objects.all().order_by("-created_at")


class CompanyAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanyAuditLogSerializer
    permission_classes = [IsAuthenticated, IsCompanyAdmin]

    def get_queryset(self):
        queryset = AuditLog.objects.filter(
            company=self.request.user.company,
        ).select_related("user")
        for field in ("action", "severity", "object_type", "user"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset


class CompanyActiveSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActiveSessionSerializer
    permission_classes = [IsAuthenticated, IsCompanyAdmin]

    def get_queryset(self):
        return ActiveSession.objects.filter(
            company=self.request.user.company,
        ).select_related("user")

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        session = self.get_object()
        if not session.is_active:
            return Response({"message": "Session is already terminated."})
        session.is_active = False
        session.terminated_at = timezone.now()
        session.save(update_fields=["is_active", "terminated_at"])
        create_audit_log(
            user=request.user,
            company=request.user.company,
            request=request,
            action="SECURITY",
            description=(
                f"Terminated active session for {session.user.email}."
            ),
            obj=session,
        )
        return Response({"message": "Session terminated."})
