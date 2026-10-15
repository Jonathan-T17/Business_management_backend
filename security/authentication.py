from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.authorization import Authorization


class ActiveCompanyJWTAuthentication(JWTAuthentication):
    """Reject access tokens for disabled users or companies."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result:
            from companies.invitation_access import enforce_invitation_access
            enforce_invitation_access(request, result[0])
            from company_setup.access import enforce_setup_access
            enforce_setup_access(request, result[0])
        return result

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if not Authorization.can_authenticate(user):
            raise AuthenticationFailed(
                "Account or company access is inactive.",
                code="user_inactive",
            )

        from django.utils import timezone
        from .models import ActiveSession
        from uuid import UUID
        try:
            session_id = UUID(str(validated_token.get("sid", "")))
        except (ValueError, TypeError):
            raise AuthenticationFailed("Session requires renewal.", code="session_inactive")
        sessions = ActiveSession.objects.filter(
            pk=session_id, user=user, is_active=True, expires_at__gt=timezone.now(),
        )
        from core.capability_service import CapabilityService
        if CapabilityService.is_platform_operator(user):
            sessions = sessions.filter(mfa_verified_at__isnull=False)
        if not sessions.exists():
            raise AuthenticationFailed("Session is no longer active.", code="session_inactive")
        return user
