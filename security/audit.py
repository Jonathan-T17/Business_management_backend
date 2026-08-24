# security/audit.py
from security.services import create_audit_log

class SecurityAudit:
    @staticmethod
    def log(*, request=None, user=None, action, obj=None, description="", status="SUCCESS"):
        create_audit_log(
            user=user or (request.user if request else None),
            request=request,
            action=action,
            obj=obj,
            description=description,
            status=status,
        )
