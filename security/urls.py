from rest_framework.routers import DefaultRouter
from .views import (
    TrustedDeviceViewSet,
    TrustedDeviceAdminViewSet,
    AuditLogAdminViewSet,
    LoginHistoryAdminViewSet,
    CompanyAuditLogViewSet,
    CompanyActiveSessionViewSet,
)

router = DefaultRouter()
router.register(r"trusted-devices", TrustedDeviceViewSet, basename="trusted-device")
router.register(r"admin/trusted-devices", TrustedDeviceAdminViewSet, basename="trusted-device-admin")
router.register(r"admin/audit-logs", AuditLogAdminViewSet, basename="audit-log-admin")
router.register(r"admin/login-history", LoginHistoryAdminViewSet, basename="login-history-admin")
router.register(r"company-audit-logs", CompanyAuditLogViewSet, basename="company-audit-log")
router.register(r"company-active-sessions", CompanyActiveSessionViewSet, basename="company-active-session")

urlpatterns = router.urls
