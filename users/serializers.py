from user_agents import parse
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from smtplib import SMTPException
from .exceptions import VerificationEmailUnavailable
from rest_framework.exceptions import AuthenticationFailed

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from security.models import TrustedDevice
from users.services import UserService
from .models import User
from core.roles import Roles
from core.action_policy import actions_for, capabilities_for
class UserSerializer(serializers.ModelSerializer):
    context = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "theme_preference",
            "role",
            "context",
            "company",
            "branch",
            "is_active",
            "account_state",
            "email_verified",
            "must_change_password",
            "date_joined",
            "capabilities",
            "allowed_actions",
        )
        read_only_fields = ("role", "company", "branch", "account_state", "email_verified", "must_change_password")

    def get_context(self, obj):
        from core.authorization import Authorization
        return "PLATFORM" if Authorization.is_platform_superuser(obj) else "TENANT"

    def get_capabilities(self, obj):
        return capabilities_for(obj)

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        return actions_for(request.user if request else obj, target=obj)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)


class ThemePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("theme_preference",)
        extra_kwargs = {"theme_preference": {"required": True}}






class UserRegisterSerializer(serializers.ModelSerializer):
    # Registration services distinguish new users from imported invitation placeholders.
    email = serializers.EmailField(validators=[])
    # make company_name optional for invite flows
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    invite = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "password", "company_name", "invite"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        invite_token = attrs.get("invite") or self.context.get("invite")
        company_name = attrs.get("company_name")

        # If no invite token, company_name must be present and non-empty
        if not invite_token and not company_name:
            raise serializers.ValidationError({"company_name": ["Company name is required."]})

        return attrs

    def create(self, validated_data):
        invite_token = validated_data.pop("invite", None)

        # Normal signup (create company + admin)
        if not invite_token:
            company_name = validated_data.pop("company_name", None)
            try:
                user = UserService.register_company_admin(
                    email=validated_data["email"],
                    full_name=validated_data["full_name"],
                    password=validated_data["password"],
                    company_name=company_name,
                )
            except ValidationError as e:
                # re-raise so DRF returns field errors
                raise e
            return user

        # Invitation signup (join existing company)
        try:
            user = UserService.register_invited_user(
                email=validated_data["email"],
                full_name=validated_data["full_name"],
                password=validated_data["password"],
                invite_token=invite_token,
            )
        except ValidationError as e:
            raise e

        return user

    




from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from security.services import (
    clear_failed_attempts,
    create_active_session,
    create_audit_log,
    generate_otp,
    is_account_locked,
    record_login,
    register_failed_attempt,
    trusted_device_hash,
)
from core.authorization import Authorization

from security.utils import (
    get_client_ip,
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        request = self.context["request"]
        email = attrs["email"]
        ip = get_client_ip(request)

        candidate = User.objects.select_related("company").filter(
            email=email
        ).first()
        if candidate and not Authorization.can_authenticate(candidate):
            raise serializers.ValidationError(
                "This account or company is inactive."
            )

        # Lockout check
        if is_account_locked(email, ip):
            raise serializers.ValidationError("Account temporarily locked.")

        try:
            from django.contrib.auth import authenticate
            self.user = authenticate(request=request, email=email, password=attrs["password"])
            if self.user is None:
                raise AuthenticationFailed("No active account found with the given credentials")
        except AuthenticationFailed:
            register_failed_attempt(email, ip)
            create_audit_log(
                action="SECURITY",
                request=request,
                status="FAILED",
                description="Failed login attempt",
            )
            raise

        if not Authorization.can_authenticate(self.user):
            register_failed_attempt(email, ip, reason="Inactive account or company")
            raise serializers.ValidationError(
                "This account or company is inactive."
            )

        clear_failed_attempts(email, ip)

        raw_device_token = request.headers.get("X-SmartBiz-Device-Token") or request.data.get("device_token", "")
        trusted = TrustedDevice.objects.filter(
            user=self.user,
            token_hash=trusted_device_hash(str(raw_device_token)),
            is_active=True, revoked_at__isnull=True
        ).exists() if raw_device_token else False

        if not trusted:
            # Generate OTP and stop here
            challenge, code = generate_otp(self.user)
            try:
                delivered = send_mail(
                    "Your login verification code",
                    f"Your verification code is {code}. It expires in five minutes.",
                    settings.DEFAULT_FROM_EMAIL, [self.user.email], fail_silently=False,
                )
                if delivered != 1:
                    raise OSError("Verification email was not accepted for delivery.")
            except (OSError, SMTPException) as error:
                challenge.invalidated_at = timezone.now()
                challenge.save(update_fields=["invalidated_at"])
                create_audit_log(
                    user=self.user, action="SECURITY", request=request, status="FAILED",
                    description="Verification email delivery failed.",
                    metadata={"error_type": type(error).__name__},
                )
                raise VerificationEmailUnavailable() from error
            create_audit_log(
                user=self.user,
                action="SECURITY",
                request=request,
                status="FAILED",
                description="OTP required for untrusted device",
            )
            return {
                "otp_required": True,
                "message": "OTP required. Check your email.",
                "email": self.user.email,
                "challenge_id": str(challenge.challenge_id),
                "verify_url": reverse("auth-verify-otp"),
                "expires_in": 300,
            }

        # Normal flow if trusted
        refresh = RefreshToken.for_user(self.user)
        data = {"refresh": str(refresh), "access": str(refresh.access_token)}
        session = create_active_session(
            request,
            self.user,
            str(refresh["jti"]),
        )
        record_login(request, self.user, successful=True, session=session)
        create_audit_log(user=self.user, action="LOGIN", request=request, description="User logged in")

        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "full_name": self.user.full_name,
            "role": self.user.role,
        }
        return data


class ActiveCompanyTokenRefreshSerializer(TokenRefreshSerializer):

    @transaction.atomic
    def validate(self, attrs):
        from security.models import ActiveSession
        from django.utils import timezone
        token = RefreshToken(attrs["refresh"])
        user = User.objects.filter(pk=token["user_id"]).first()

        if user is None or not Authorization.can_authenticate(user):
            raise serializers.ValidationError(
                "Account or company access is inactive."
            )

        session = ActiveSession.objects.select_for_update().filter(
            user=user, refresh_token_jti=token["jti"], is_active=True,
        ).first()
        if session is None or (session.expires_at and session.expires_at <= timezone.now()):
            raise serializers.ValidationError("Session is no longer active.")
        data = super().validate(attrs)
        if "refresh" in data:
            rotated = RefreshToken(data["refresh"])
            session.refresh_token_jti = rotated["jti"]
            from datetime import datetime, timezone as dt_timezone
            session.expires_at = datetime.fromtimestamp(rotated["exp"], tz=dt_timezone.utc)
            session.save(update_fields=["refresh_token_jti", "expires_at", "last_activity"])
        return data
