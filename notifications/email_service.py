from email.utils import formataddr, parseaddr

from django.conf import settings
from django.core.mail import (
    EmailMultiAlternatives,
)
from django.template.loader import (
    render_to_string,
)
from django.utils import timezone

from .models import (
    EmailDeliveryLog,
)


class CompanyEmailService:

    @staticmethod
    def send(
        *,
        recipient_email,
        subject,
        template,
        email_type,
        company=None,
        user=None,
        context=None,
        reference_id="",
        force=False,
    ):
        if not recipient_email:
            return None

        if (
            company
            and not company.email_notifications_enabled
            and not force
        ):
            return None

        log = EmailDeliveryLog.objects.create(
            company=company,
            user=user,
            recipient_email=
                recipient_email,
            email_type=email_type,
            subject=subject,
            reference_id=
                reference_id or "",
            status="PENDING",
        )

        try:
            context = {
                **(context or {}),
                "company": company,
                "recipient": user,
                "subject": subject,
            }

            html_body = render_to_string(
                template,
                context,
            )

            from_name = (
                company.communication_name
                if company
                else getattr(
                    settings,
                    "PLATFORM_EMAIL_NAME",
                    "SmartBiz",
                )
            )

            from_address = getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "notifications@example.com",
            )

            _, from_address = parseaddr(from_address)

            from_email = formataddr(
                (
                    (
                        f"{from_name} "
                        f"via SmartBiz"
                    )
                    if company
                    else from_name,
                    from_address,
                )
            )

            reply_to = []

            if (
                company
                and company.communication_reply_to
            ):
                reply_to.append(
                    company.communication_reply_to
                )

            email = EmailMultiAlternatives(
                subject=subject,
                body=(
                    context.get(
                        "plain_message",
                        subject,
                    )
                ),
                from_email=from_email,
                to=[
                    recipient_email
                ],
                reply_to=reply_to,
            )

            email.attach_alternative(
                html_body,
                "text/html",
            )

            email.send(
                fail_silently=False
            )

            log.status = "SENT"
            log.sent_at = timezone.now()

            log.save(
                update_fields=[
                    "status",
                    "sent_at",
                ]
            )

        except Exception as exc:
            log.status = "FAILED"
            log.error_message = str(exc)

            log.save(
                update_fields=[
                    "status",
                    "error_message",
                ]
            )

            raise

        return log