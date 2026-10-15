from django.contrib import admin

from .models import (
    ActiveSession,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
)


class ReadOnlySecurityAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlySecurityAdmin):
    list_display = (
        "action",
        "user",
        "company",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "action",
        "created_at",
    )

    search_fields = (
        "action",
        "description",
        "user__email",
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(ReadOnlySecurityAdmin):
    list_display = (
        "user",
        "ip_address",
        "device",
        "successful",
        "created_at",
    )

    list_filter = (
        "successful",
        "created_at",
    )


@admin.register(ActiveSession)
class ActiveSessionAdmin(ReadOnlySecurityAdmin):
    list_display = (
        "user",
        "device",
        "ip_address",
        "last_activity",
        "is_active",
    )


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(ReadOnlySecurityAdmin):
    list_display = (
        "email_hint",
        "ip_address",
        "attempts",
        "locked_until",
    )
