from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class RecoveryAdminSite(AdminSite):
    site_header = "SmartBiz restricted administration"
    site_title = "SmartBiz recovery"
    index_title = "Restricted operational recovery"

    def has_permission(self, request):
        return bool(
            super().has_permission(request)
            and request.user.is_superuser
            and not getattr(request.user, "is_deleted", False)
        )


class RecoveryAdminConfig(AdminConfig):
    default_site = "core.admin_site.RecoveryAdminSite"
