from django.urls import path
from .passkeys import OwnPasskeys, RegistrationOptions, RegistrationVerify, RevokePasskey, LoginOptions, LoginVerify
from rest_framework.routers import DefaultRouter
from .views import (
    TrustedDeviceViewSet,
    TrustedDeviceAdminViewSet,
    AuditLogAdminViewSet,
    LoginHistoryAdminViewSet,
    CompanyAuditLogViewSet,
    CompanyActiveSessionViewSet,
    MySessionViewSet,
)

router = DefaultRouter()
router.register(r"security/sessions", MySessionViewSet, basename="my-security-session")
router.register(r"security/trusted-devices", TrustedDeviceViewSet, basename="my-trusted-device")
router.register(r"trusted-devices", TrustedDeviceViewSet, basename="trusted-device")
router.register(r"admin/trusted-devices", TrustedDeviceAdminViewSet, basename="trusted-device-admin")
router.register(r"admin/audit-logs", AuditLogAdminViewSet, basename="audit-log-admin")
router.register(r"admin/login-history", LoginHistoryAdminViewSet, basename="login-history-admin")
router.register(r"company-audit-logs", CompanyAuditLogViewSet, basename="company-audit-log")
router.register(r"company-active-sessions", CompanyActiveSessionViewSet, basename="company-active-session")

urlpatterns = [
    path("security/passkeys/", OwnPasskeys.as_view()),
    path("security/passkeys/register/options/", RegistrationOptions.as_view()),
    path("security/passkeys/register/verify/", RegistrationVerify.as_view()),
    path("security/passkeys/<uuid:pk>/revoke/", RevokePasskey.as_view()),
    path("auth/passkey/options/", LoginOptions.as_view()),
    path("auth/passkey/verify/", LoginVerify.as_view()),
] + router.urls
