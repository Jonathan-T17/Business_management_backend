from django.contrib import admin

from .models import (
    ActiveSession,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
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
class LoginHistoryAdmin(admin.ModelAdmin):
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
class ActiveSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "device",
        "ip_address",
        "last_activity",
        "is_active",
    )


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "ip_address",
        "attempts",
        "locked_until",
    )