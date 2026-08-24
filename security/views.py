from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TrustedDevice, AuditLog, LoginHistory
from .serializers import TrustedDeviceSerializer, AuditLogSerializer, LoginHistorySerializer
from security.services import create_audit_log
from users.permissions import IsSuperUserOrPlatformAdmin


# User-level viewset
class TrustedDeviceViewSet(viewsets.ModelViewSet):
    serializer_class = TrustedDeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TrustedDevice.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        device = self.get_object()
        device.is_active = False
        device.save()

        create_audit_log(
            user=request.user,
            action="SECURITY",
            request=request,
            description=f"Trusted device revoked: {device.device_name}",
        )

        return Response({"message": "Device revoked successfully"}, status=status.HTTP_200_OK)


# Platform admin viewsets
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
