from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError


class RecoveryMFAForm(AdminAuthenticationForm):
    verification_code = forms.CharField(required=False, label="Email verification code", max_length=6)
    challenge_id = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean(self):
        from uuid import UUID
        from django.conf import settings
        from django.core.mail import send_mail
        from django.utils import timezone
        from core.capabilities import Capabilities
        from core.capability_service import CapabilityService
        from security.services import generate_otp, verify_otp, is_account_locked, register_failed_attempt
        from security.utils import get_client_ip
        email = str(self.data.get("username", ""))
        ip = get_client_ip(self.request)
        if is_account_locked(email, ip):
            raise ValidationError("Sign-in is temporarily unavailable. Try again later.")
        try:
            values = super().clean()
        except ValidationError:
            register_failed_attempt(email, ip)
            raise
        user = self.get_user()
        if not CapabilityService.has(user, Capabilities.PLATFORM_ADMIN):
            raise ValidationError("This account cannot use recovery administration.")
        raw_id = values.get("challenge_id")
        code = values.get("verification_code")
        if not raw_id:
            from rest_framework.exceptions import ValidationError as APIValidationError
            try:
                challenge, code_to_send = generate_otp(user)
            except APIValidationError:
                raise ValidationError("Too many verification requests. Try again later.")
            try:
                delivered = send_mail("Recovery administration sign-in code",
                    f"Your verification code is {code_to_send}. It expires in five minutes.",
                    settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                if delivered != 1:
                    raise RuntimeError("Delivery unavailable")
            except Exception:
                raise ValidationError("Verification email could not be sent. Try again shortly.")
            self.data = self.data.copy()
            self.data["challenge_id"] = str(challenge.challenge_id)
            raise ValidationError("Enter the code sent to your email and re-enter your password to finish signing in.")
        try:
            challenge_id = UUID(raw_id)
        except (ValueError, TypeError):
            raise ValidationError("Invalid or expired verification code.")
        if not verify_otp(user, challenge_id=challenge_id, code=code or ""):
            register_failed_attempt(email, ip, reason="Recovery verification failed")
            raise ValidationError("Invalid or expired verification code.")
        from security.services import clear_failed_attempts, create_audit_log
        clear_failed_attempts(email, ip)
        self.request.session["platform_mfa_at"] = timezone.now().timestamp()
        self.request.session["platform_mfa_user"] = str(user.pk)
        self.request._recovery_verified_user = str(user.pk)
        create_audit_log(user=user, action="RECOVERY_MFA_VERIFIED", request=self.request,
                         severity="WARNING", description="Recovery administrator verified email challenge.")
        return values
