from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "company",
        "branch",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )
    list_filter = (
        "notification_type",
        "is_read",
        "company",
        "branch",
    )
    search_fields = (
        "title",
        "message",
        "recipient__email",
        "reference_id",
    )
    readonly_fields = (
        "recipient",
        "company",
        "branch",
        "notification_type",
        "title",
        "message",
        "url",
        "reference_id",
        "created_at",
    )
