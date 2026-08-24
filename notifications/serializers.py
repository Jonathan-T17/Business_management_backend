from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from notifications.services import CommunicationService, create_notification
from security.services import create_audit_log
from users.models import User

from .models import (Notification, NotificationPreference,
    EmailDeliveryLog,
)



class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source="get_notification_type_display",
        read_only=True,
    )
    is_unread = serializers.BooleanField(read_only=True)

    # New computed field
    is_security = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "message",
            "reference_id",
            "url",
            "is_read",
            "is_unread",
            "branch",
            "created_at",
            "is_security",   # include new field
        ]
        read_only_fields = fields

    def get_is_security(self, obj):
        """Return True if this notification is a critical security event."""
        return obj.notification_type == "SECURITY"
    

# class NotificationSerializer(serializers.ModelSerializer):
#     notification_type_display = serializers.CharField(
#         source="get_notification_type_display",
#         read_only=True,
#     )

#     is_unread = serializers.BooleanField(
#         read_only=True,
#     )

#     class Meta:
#         model = Notification

#         fields = [
#             "id",
#             "notification_type",
#             "notification_type_display",
#             "title",
#             "message",
#             "reference_id",
#             "url",
#             "is_read",
#             "is_unread",
#             "branch",
#             "created_at",
#         ]

#         read_only_fields = fields





class NotificationPreferenceSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = (
            NotificationPreference
        )

        fields = (
            "in_app_enabled",
            "email_enabled",

            "task_assignments",
            "task_updates",

            "project_updates",

            "reports",
            "comments",

            "organization_updates",

            "subscription_updates",

            "ai_insights",

            "digest_enabled",
            "digest_cadence",

            "updated_at",
        )

        read_only_fields = (
            "updated_at",
        )


class EmailDeliveryLogSerializer(
    serializers.ModelSerializer
):

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = EmailDeliveryLog

        fields = (
            "id",
            "company",
            "company_name",
            "user",
            "recipient_email",
            "email_type",
            "subject",
            "status",
            "reference_id",
            "error_message",
            "sent_at",
            "created_at",
        )

        read_only_fields = fields






def _send_security_alert(user, title, message, reference_id, email_subject, email_context):
    # Notify the user
    create_notification(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title=title,
        message=message,
        reference_id=reference_id,
    )

    # Forced email
    CommunicationService.send(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title=title,
        message=message,
        reference_id=reference_id,
        send_email=True,
        force_email=True,
        email_subject=email_subject,
        email_template="emails/security_alert.html",
        email_context=email_context,
    )

    # Superuser visibility + audit
    superusers = User.objects.filter(is_superuser=True)
    for su in superusers:
        create_notification(
            recipient=su,
            company=getattr(user, "company", None),
            notification_type="SECURITY",
            title=f"[{user.email}] {title}",
            message=f"{message} (Reference: {reference_id})",
            reference_id=reference_id,
        )
        create_audit_log(
            user=su,
            action="SECURITY_ALERT_FORWARD",
            description=f"Forwarded security alert for {user.email}: {title}",
            obj=user,
        )





def send_daily_security_digest():
    # Get all security notifications from the past 24 hours
    since = timezone.now() - timedelta(hours=24)
    security_events = Notification.objects.filter(
        notification_type="SECURITY",
        created_at__gte=since
    ).order_by("created_at")

    if not security_events.exists():
        return

    # Build digest message
    digest_lines = [
        f"- {n.created_at.strftime('%H:%M')} | {n.title}: {n.message}"
        for n in security_events
    ]
    digest_message = "\n".join(digest_lines)

    # Send to all superusers
    superusers = User.objects.filter(is_superuser=True)
    for su in superusers:
        # In-app digest notification
        create_notification(
            recipient=su,
            company=getattr(su, "company", None),
            notification_type="SECURITY_DIGEST",
            title="Daily Security Digest",
            message=f"Summary of security events in the last 24 hours:\n{digest_message}",
            reference_id="digest-" + timezone.now().strftime("%Y%m%d"),
        )

        # Forced digest email
        CommunicationService.send(
            recipient=su,
            company=getattr(su, "company", None),
            notification_type="SECURITY",
            title="Daily Security Digest",
            message="Summary of security events in the last 24 hours.",
            reference_id="digest-" + timezone.now().strftime("%Y%m%d"),
            send_email=True,
            force_email=True,
            email_subject="Daily Security Digest",
            email_template="emails/security_digest.html",
            email_context={
                "digest_lines": digest_lines,
            },
        )


def send_security_digest(cadence="DAILY"):
    now = timezone.now()
    if cadence == "DAILY":
        since = now - timedelta(hours=24)
    elif cadence == "WEEKLY":
        since = now - timedelta(days=7)
    else:
        return  # NONE or unsupported

    security_events = Notification.objects.filter(
        notification_type="SECURITY",
        created_at__gte=since
    ).order_by("created_at")

    if not security_events.exists():
        return

    digest_lines = [
        f"- {n.created_at.strftime('%Y-%m-%d %H:%M')} | {n.title}: {n.message}"
        for n in security_events
    ]
    digest_message = "\n".join(digest_lines)

    superusers = User.objects.filter(is_superuser=True)
    for su in superusers:
        pref = getattr(su, "notificationpreference", None)
        if not pref or pref.digest_cadence != cadence:
            continue

        create_notification(
            recipient=su,
            company=getattr(su, "company", None),
            notification_type="SECURITY_DIGEST",
            title=f"{cadence.capitalize()} Security Digest",
            message=f"Summary of security events:\n{digest_message}",
            reference_id=f"digest-{cadence}-{now.strftime('%Y%m%d')}",
        )

        CommunicationService.send(
            recipient=su,
            company=getattr(su, "company", None),
            notification_type="SECURITY",
            title=f"{cadence.capitalize()} Security Digest",
            message="Summary of recent security events.",
            reference_id=f"digest-{cadence}-{now.strftime('%Y%m%d')}",
            send_email=True,
            force_email=True,
            email_subject=f"{cadence.capitalize()} Security Digest",
            email_template="emails/security_digest.html",
            email_context={"digest_lines": digest_lines},
        )
