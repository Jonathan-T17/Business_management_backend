from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.authorization import Authorization


class ActiveCompanyJWTAuthentication(JWTAuthentication):
    """Reject access tokens for disabled users or companies."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        if not Authorization.can_authenticate(user):
            raise AuthenticationFailed(
                "Account or company access is inactive.",
                code="user_inactive",
            )

        return user