from user_agents import parse

from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from security.models import TrustedDevice
from users.services import UserService
from .models import User
from core.roles import Roles
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "company",
            "branch",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("role", "company", "branch")


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)






class UserRegisterSerializer(serializers.ModelSerializer):
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
)

from security.utils import (
    get_client_ip,
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        request = self.context["request"]
        email = attrs["email"]
        ip = get_client_ip(request)

        # Lockout check
        if is_account_locked(email, ip):
            raise serializers.ValidationError("Account temporarily locked.")

        try:
            data = super().validate(attrs)
        except Exception:
            register_failed_attempt(email, ip)
            create_audit_log(
                action="SECURITY",
                request=request,
                status="FAILED",
                description=f"Failed login for {email}",
            )
            raise

        clear_failed_attempts(email, ip)

        # Device fingerprint
        ua = parse(request.META.get("HTTP_USER_AGENT", ""))
        fingerprint = f"{ua.browser.family}-{ua.os.family}-{ua.device.family}"

        trusted = TrustedDevice.objects.filter(
            user=self.user,
            fingerprint=fingerprint,
            is_active=True
        ).exists()

        if not trusted:
            # Generate OTP and stop here
            generate_otp(self.user, fingerprint)
            create_audit_log(
                user=self.user,
                action="SECURITY",
                request=request,
                status="FAILED",
                description="OTP required for untrusted device",
            )
            raise serializers.ValidationError({
                "otp_required": True,
                "message": "OTP required. Check your email.",
                "email": self.user.email,
                "verify_url": "/api/verify-otp/",
            })

        # Normal flow if trusted
        refresh = RefreshToken(data["refresh"])
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
