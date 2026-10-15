from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class RecoveryAdminSite(AdminSite):
    login_template = "admin/recovery_login.html"
    @property
    def login_form(self):
        from .recovery_mfa import RecoveryMFAForm
        return RecoveryMFAForm
    site_header = "SmartBiz restricted administration"
    site_title = "SmartBiz recovery"
    index_title = "Restricted operational recovery"

    def login(self, request, extra_context=None):
        response = super().login(request, extra_context=extra_context)
        # Django may flush an old account's session when completing a different login.
        verified = getattr(request, "_recovery_verified_user", None)
        if verified and request.user.is_authenticated and verified == str(request.user.pk):
            from django.utils import timezone
            request.session["platform_mfa_at"] = timezone.now().timestamp()
            request.session["platform_mfa_user"] = verified
        return response

    def has_permission(self, request):
        from core.capability_service import CapabilityService
        from core.capabilities import Capabilities
        from django.utils import timezone
        session = getattr(request, "session", {})
        try:
            elapsed = timezone.now().timestamp() - float(session.get("platform_mfa_at", 0))
        except (TypeError, ValueError):
            return False
        return bool(super().has_permission(request)
                    and CapabilityService.has(request.user, Capabilities.PLATFORM_ADMIN)
                    and session.get("platform_mfa_user") == str(request.user.pk)
                    and 0 <= elapsed < 900)


class RecoveryAdminConfig(AdminConfig):
    default_site = "core.admin_site.RecoveryAdminSite"
