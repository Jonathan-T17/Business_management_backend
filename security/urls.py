from rest_framework.routers import DefaultRouter
from .views import (
    TrustedDeviceViewSet,
    TrustedDeviceAdminViewSet,
    AuditLogAdminViewSet,
    LoginHistoryAdminViewSet,
)

router = DefaultRouter()
router.register(r"trusted-devices", TrustedDeviceViewSet, basename="trusted-device")
router.register(r"admin/trusted-devices", TrustedDeviceAdminViewSet, basename="trusted-device-admin")
router.register(r"admin/audit-logs", AuditLogAdminViewSet, basename="audit-log-admin")
router.register(r"admin/login-history", LoginHistoryAdminViewSet, basename="login-history-admin")

urlpatterns = router.urls
