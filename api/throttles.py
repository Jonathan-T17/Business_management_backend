from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
class TrustedClientAnonThrottle(AnonRateThrottle):
    def get_ident(self, request):
        from security.utils import get_client_ip
        return get_client_ip(request) or "unknown"
class LoginRateThrottle(TrustedClientAnonThrottle): scope='login'
class VerificationRateThrottle(TrustedClientAnonThrottle): scope='verification'
class PasswordResetRateThrottle(TrustedClientAnonThrottle): scope='password_reset'
class InviteRateThrottle(UserRateThrottle): scope='invite'
class ExportRateThrottle(UserRateThrottle): scope='export'
class ImportRateThrottle(UserRateThrottle): scope='import'
class PublicVerificationRateThrottle(TrustedClientAnonThrottle): scope='public_verify'
class AIInsightRateThrottle(UserRateThrottle): scope='ai'
class SensitiveActionRateThrottle(UserRateThrottle): scope='sensitive_action'
