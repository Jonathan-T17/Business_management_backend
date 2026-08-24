import logging

audit_logger = logging.getLogger("audit")


def log_event(event, user=None, extra=None):
    audit_logger.info(
        {
            "event": event,
            "user_id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "extra": extra,
        }
    )