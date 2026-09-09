from django.db import transaction
from django.contrib.auth import get_user_model
from core.authorization import Authorization
from core.roles import Roles

from .models import (
    Notification,
    NotificationPreference,
)

from .email_service import (
    CompanyEmailService,
)


SUPERUSER_ONLY_NOTIFICATION_TYPES = frozenset({
    "SECURITY",
    "NEW_LOGIN",
    "OTP_SUCCESS",
    "OTP_FAILED",
    "OTP_EXPIRED",
    "ACCOUNT_LOCKED",
    "ACCOUNT_INTERVENTION",
    "SECURITY_DIGEST",
})


def create_notification(
    *,
    recipient,
    title,
    message,
    notification_type="SYSTEM",
    company=None,
    branch=None,
    url="",
    reference_id=None,
):
    company = (
        company
        or getattr(
            recipient,
            "company",
            None,
        )
    )

    if notification_type in SUPERUSER_ONLY_NOTIFICATION_TYPES:
        notifications = []
        user_model = get_user_model()
        superusers = (
            [recipient]
            if Authorization.is_platform_superuser(recipient)
            else user_model.objects.filter(
                is_superuser=True,
            ).union(
                user_model.objects.filter(role=Roles.SUPERUSER)
            )
        )
        for superuser in superusers:
            notifications.append(
                Notification.objects.create(
                    recipient=superuser,
                    company=company or getattr(superuser, "company", None),
                    branch=None,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    url=url,
                    reference_id=reference_id,
                )
            )
        return notifications[0] if notifications else None

    return Notification.objects.create(
        recipient=recipient,
        company=company,
        branch=branch or getattr(recipient, "branch", None),
        notification_type=notification_type,
        title=title,
        message=message,
        url=url,
        reference_id=reference_id,
    )


class CommunicationService:

    EMAIL_PREFERENCE_MAPPING = {
        "TASK_ASSIGNED":
            "task_assignments",

        "TASK_UPDATED":
            "task_updates",

        "PROJECT_CREATED":
            "project_updates",

        "PROJECT_UPDATED":
            "project_updates",

        "MEMBERSHIP_CREATED":
            "project_updates",

        "REPORT_CREATED":
            "reports",

        "REPORT_SUBMITTED":
            "reports",

        "REPORT_COMMENT":
            "comments",

        "COMMENT_REPLY":
            "comments",

        "AI_INSIGHT":
            "ai_insights",

        "SUBSCRIPTION":
            "subscription_updates",
    }


    @staticmethod
    def preferences_for(user):

        preferences, _ = (
            NotificationPreference.objects
            .get_or_create(
                user=user
            )
        )

        return preferences


    @classmethod
    def email_allowed(
        cls,
        user,
        notification_type,
    ):
        preferences = (
            cls.preferences_for(user)
        )

        if not preferences.email_enabled:
            return False

        preference_field = (
            cls.EMAIL_PREFERENCE_MAPPING
            .get(notification_type)
        )

        if not preference_field:
            return True

        return bool(
            getattr(
                preferences,
                preference_field,
                True,
            )
        )


    @classmethod
    def send(
        cls,
        *,
        recipient,
        title,
        message,
        notification_type,
        company=None,
        branch=None,
        url="",
        reference_id=None,

        send_email=False,
        email_subject=None,
        email_template=None,
        email_context=None,

        force_email=False,
    ):

        company = (
            company
            or getattr(
                recipient,
                "company",
                None,
            )
        )

        preferences = (
            cls.preferences_for(
                recipient
            )
        )

        policy = None
        if company:
            from company_setup.models import NotificationPolicy

            policy = NotificationPolicy.objects.filter(
                company=company,
                event_code=notification_type,
                is_active=True,
            ).first()

        in_app_enabled = preferences.in_app_enabled
        email_enabled = True
        user_can_disable_email = True
        if policy:
            in_app_enabled = (
                in_app_enabled
                and policy.in_app_enabled
            )
            email_enabled = policy.email_enabled
            user_can_disable_email = policy.user_can_disable_email

        notification = None

        if in_app_enabled:
            notification = (
                create_notification(
                    recipient=recipient,
                    company=company,
                    branch=branch,
                    notification_type=
                        notification_type,
                    title=title,
                    message=message,
                    url=url,
                    reference_id=
                        reference_id,
                )
            )

        email_recipients = [recipient]
        if notification_type in SUPERUSER_ONLY_NOTIFICATION_TYPES:
            user_model = get_user_model()
            email_recipients = list(
                user_model.objects.filter(is_superuser=True).union(
                    user_model.objects.filter(role=Roles.SUPERUSER)
                )
            )

        should_email = (
            send_email
            and email_enabled
            and bool(
                email_template
            )
            and email_recipients
        )

        if should_email:
            for email_recipient in email_recipients:
                if (
                    not force_email
                    and user_can_disable_email
                    and not cls.email_allowed(
                        email_recipient,
                        notification_type,
                    )
                ):
                    continue
                transaction.on_commit(
                    lambda email_recipient=email_recipient: (
                        CompanyEmailService.send(
                            company=company,
                            user=email_recipient,
                            recipient_email=email_recipient.email,
                            subject=email_subject or title,
                            template=email_template,
                            email_type=notification_type,
                            context=email_context,
                            reference_id=(
                                str(reference_id)
                                if reference_id
                                else ""
                            ),
                            force=force_email,
                        )
                    )
                )

        return notification


    @staticmethod
    def send_to_address(
        *,
        recipient_email,
        company,
        subject,
        email_type,
        template,
        context=None,
        reference_id="",
        force=False,
    ):

        transaction.on_commit(
            lambda: (
                CompanyEmailService.send(
                    company=company,
                    user=None,
                    recipient_email=
                        recipient_email,
                    subject=subject,
                    template=template,
                    email_type=
                        email_type,
                    context=context,
                    reference_id=
                        reference_id,
                    force=force,
                )
            )
        )




# from django.core.exceptions import ValidationError

# from .models import Notification


# def create_notification(
#     *,
#     recipient,
#     title,
#     message,
#     notification_type=Notification.SYSTEM,
#     company=None,
#     branch=None,
#     url="",
#     reference_id=None,
# ):
#     """
#     Create an in-app notification.

#     Notifications should normally be created by backend services,
#     not directly by API clients.
#     """

#     if recipient is None:
#         raise ValidationError(
#             "Notification recipient is required."
#         )

#     recipient_company = getattr(
#         recipient,
#         "company",
#         None,
#     )

#     if recipient_company is None:
#         raise ValidationError(
#             "Notification recipient must belong to a company."
#         )

#     if company is None:
#         company = recipient_company

#     if company.id != recipient_company.id:
#         raise ValidationError(
#             "Notification company must match the recipient's company."
#         )

#     if branch is None:
#         branch = getattr(
#             recipient,
#             "branch",
#             None,
#         )

#     if branch is not None and branch.company_id != company.id:
#         raise ValidationError(
#             "Notification branch must belong to the notification company."
#         )

#     valid_types = {
#         choice[0]
#         for choice in Notification.NOTIFICATION_TYPES
#     }

#     if notification_type not in valid_types:
#         raise ValidationError(
#             f"Invalid notification type: {notification_type}"
#         )

#     return Notification.objects.create(
#         recipient=recipient,
#         company=company,
#         branch=branch,
#         notification_type=notification_type,
#         title=title,
#         message=message,
#         url=url or "",
#         reference_id=reference_id,
#     )