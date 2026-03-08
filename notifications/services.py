from .models import Notification


def create_notification(
    recipient,
    company,
    notification_type,
    title,
    message,
    reference_id=None
):

    Notification.objects.create(
        recipient=recipient,
        company=company,
        notification_type=notification_type,
        title=title,
        message=message,
        reference_id=reference_id
    )


