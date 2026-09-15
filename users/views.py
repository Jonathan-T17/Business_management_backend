from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from django.db import transaction
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError as APIValidationError

from core.tenant import TenantService
from core.authorization import Authorization
from core.roles import Roles
from security.models import ActiveSession
from security.services import create_audit_log, record_login, terminate_user_sessions
from security.utils import get_client_ip

from .models import User
from .services import TenantUserLifecycleService
from .serializers import (
    UserSerializer,
    UserUpdateSerializer,
    ThemePreferenceSerializer,
    UserRegisterSerializer,
    CustomTokenObtainPairSerializer,
    ActiveCompanyTokenRefreshSerializer,
)

from core.permissions import IsSuperUserOrCompanyAdmin
from .tokens import email_verification_token
from .utils import send_verification_email, send_password_reset_email, password_reset_token
from security.audit import SecurityAudit
from .permissions import IsSelf
from rest_framework.decorators import action

User = get_user_model()


def _is_last_active_company_admin(user):
    if user is None or not getattr(user, "company_id", None) or user.role != Roles.ADMIN:
        return False

    return not User.objects.filter(
        company_id=user.company_id,
        role=Roles.ADMIN,
        is_active=True,
        is_deleted=False,
    ).exclude(pk=user.pk).exists()


def _guard_last_company_admin(target_user, action_label):
    if target_user.role == Roles.ADMIN and _is_last_active_company_admin(target_user):
        raise ValidationError(f"Cannot {action_label} the last active company administrator.")


# ================= USERS =================

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsSuperUserOrCompanyAdmin]

    def get_queryset(self):
        return TenantService.users(self.request.user)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        serializer = UserSerializer(
            request.user,
            context={"request": request},
        )
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated], url_path="me/preferences")
    def preferences(self, request):
        serializer = ThemePreferenceSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated, IsSelf]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)



# ================= REGISTER =================

class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            with transaction.atomic():
                user = serializer.save()
                token = email_verification_token.make_token(user)

                transaction.on_commit(lambda: send_verification_email(user, token))

                SecurityAudit.log(
                    user=user,
                    action="USER",
                    request=request,
                    description="User registered",
                    status="SUCCESS"
                )

            return Response(
                {"message": "Account created. Check your email to verify."},
                status=201,
            )

        except ValidationError as e:
            return Response(getattr(e, 'message_dict', {'error': e.messages}), status=400)
        except (APIValidationError, PermissionDenied):
            raise
        except Exception as e:
            print("Register error:", str(e))

            return Response(
                {"error": "Registration failed. Try again later."},
                status=500,
            )


# ================= VERIFY EMAIL =================

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"error": "Invalid link"}, status=400)
        
        if user.email_verified:
            return Response({"message": "Email already verified"}, status=400)

        if email_verification_token.check_token(user, token):
            TenantUserLifecycleService.verify_email(user=user, request=request)

            SecurityAudit.log(
                user=user,
                action="SECURITY",
                request=request,
                description="Email verified",
                status="SUCCESS"
            )
            return Response ({"message": "Email verified Sucessfully"}, status=200)
        else:
            SecurityAudit.log(
                user=user,
                action="SECURITY",
                request=request,
                description="Email verification failed",
                status="FAILED"
            )

            return Response({"message": "Email verification failed"}, status=400)

        return Response({"error": "Invalid or expired token"}, status=400)


# ================= RESEND VERIFICATION =================

class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)

            if not user.email_verified:
                token = email_verification_token.make_token(user)
                send_verification_email(user, token)

        except User.DoesNotExist:
            pass  # hide existence

        return Response(
            {"message": "If an account exists, email has been sent."},
            status=200,
        )


# ================= AUTH =================

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ActiveCompanyTokenRefreshView(TokenRefreshView):
    serializer_class = ActiveCompanyTokenRefreshSerializer


# ================= PASSWORD RESET =================

class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = request.data.get("email")

        try:
            user = User.objects.get(email=email)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token.make_token(user)

            send_password_reset_email(user, uidb64, token)

            SecurityAudit.log(
                user=user,
                action="SECURITY",
                request=request,
                description="Password reset requested",
                status="SUCCESS"
            )

        except User.DoesNotExist:
            pass

        return Response(
            {"message": "If an account exists, a reset email has been sent."},
            status=200,
        )


class ConfirmPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"error": "Invalid request"}, status=400)

        if not password_reset_token.check_token(user, token):
            return Response({"error": "Invalid or expired token"}, status=400)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=400)

        TenantUserLifecycleService.password_reset_completed(
            user=user, new_password=new_password, request=request
        )

        SecurityAudit.log(
            user=user,
            action="SECURITY",
            request=request,
            description="Password updated successfully",
            status="SUCCESS"
        )

        return Response({"message": "Password updated successfully"}, status=200)
    





class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()

            # Terminate ActiveSession
            session = ActiveSession.objects.filter(
                user=request.user,
                refresh_token_jti=token["jti"]
            ).first()

            if session:
                session.is_active = False
                session.terminated_at = timezone.now()
                session.save()

            # Audit log
            SecurityAudit.log(
                user=request.user,
                action="LOGOUT",
                request=request,
                description="User logged out",
            )

            # Optional: record logout in LoginHistory
            record_login(
                request,
                request.user,
                successful=True,
                session=session,
                failure_reason=""
            )

            return Response(
                {"message": "Logged out successfully"},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception:
            # Failed logout attempt
            SecurityAudit.log(
                user=request.user,
                action="SECURITY",
                request=request,
                status="FAILED",
                description="Logout failed",
            )
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )





from user_agents import parse

from security.services import verify_otp, create_audit_log, record_login, create_active_session, register_failed_attempt, clear_failed_attempts, issue_trusted_device_token, is_account_locked
from security.models import TrustedDevice

User = get_user_model()


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    from api.throttles import VerificationRateThrottle
    throttle_classes = [VerificationRateThrottle]

    @transaction.atomic
    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")
        from uuid import UUID
        try:
            challenge_id = UUID(str(request.data.get("challenge_id", "")))
        except (ValueError, TypeError):
            return Response({"error": "Invalid or expired OTP"}, status=400)
        if not isinstance(code, str):
            return Response({"error": "Invalid or expired OTP"}, status=400)

        from security.models import OTP
        challenge = OTP.objects.select_related("user__company").filter(challenge_id=challenge_id).first()
        if challenge is None or (email is not None and email != challenge.user.email):
            return Response({"error": "Invalid or expired OTP"}, status=400)
        user = challenge.user
        email = user.email
        if is_account_locked(email, get_client_ip(request)):
            return Response({"error": "Invalid or expired OTP"}, status=400)

        ua = parse(request.META.get("HTTP_USER_AGENT", ""))
        if not verify_otp(user, challenge_id=challenge_id, code=code):
            # Failed OTP
            register_failed_attempt(email, get_client_ip(request), reason="Invalid OTP")
            SecurityAudit.log(
                user=user,
                action="SECURITY",
                request=request,
                status="FAILED",
                description="OTP verification failed",
            )
            return Response({"error": "Invalid or expired OTP"}, status=400)

        # Clear failed attempts on success
        clear_failed_attempts(email, get_client_ip(request))

        # Trust device if user opts in
        device_token = None
        if request.data.get("trust_device") is True:
            device_token, token_hash = issue_trusted_device_token()
            TrustedDevice.objects.create(
                user=user,
                token_hash=token_hash,
                device_name=ua.device.family or "Unknown Device",
                ip_address=get_client_ip(request),
            )

        # Re-check current account/company state immediately before token issuance.
        if not Authorization.can_authenticate(user):
            return Response({"error": "Invalid or expired OTP"}, status=400)

        # Issue tokens
        refresh = RefreshToken.for_user(user)

        # Create active session
        session = create_active_session(
            request,
            user,
            str(refresh["jti"]),
        )

        # Record login history
        record_login(request, user, successful=True, session=session)

        # Audit log
        create_audit_log(
            user=user,
            action="LOGIN",
            request=request,
            description="User logged in via OTP",
        )

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "device_token": device_token,
            "trusted_device_token": device_token,
            "otp_required": False,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            }
        })


class DeactivateUserView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUserOrCompanyAdmin]

    def post(self, request, user_id):
        try:
            target = User.objects.filter(pk=user_id, company=request.user.company).get()
            TenantUserLifecycleService.deactivate(
                actor=request.user, target=target,
                reason=request.data.get("reason", "").strip(), request=request,
            )
            return Response({"message": "User deactivated"}, status=200)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class ActivateUserView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUserOrCompanyAdmin]

    def post(self, request, user_id):
        try:
            target = User.objects.filter(pk=user_id, company=request.user.company).get()
            TenantUserLifecycleService.reactivate(
                actor=request.user, target=target,
                reason=request.data.get("reason", "").strip(), request=request,
            )
            return Response({"message": "User activated"}, status=200)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


class ChangeUserRoleView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUserOrCompanyAdmin]

    def post(self, request, user_id):
        try:
            target = User.objects.filter(pk=user_id, company=request.user.company).get()
            TenantUserLifecycleService.change_role(
                actor=request.user, target=target, new_role=request.data.get("role"),
                reason=request.data.get("reason", "").strip(), request=request,
            )
            return Response({"message": "Role updated", "role": target.role}, status=200)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
