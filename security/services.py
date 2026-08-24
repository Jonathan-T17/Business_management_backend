from django.utils import timezone
from datetime import timedelta
import secrets
from django.core.mail import send_mail
from user_agents import parse

from notifications.services import CommunicationService, create_notification
from users.models import User

from .models import LoginHistory, AuditLog, ActiveSession, FailedLoginAttempt, OTP
from .constants import MAX_LOGIN_ATTEMPTS, ACCOUNT_LOCK_MINUTES
from .utils import get_client_ip


# ---------------------------
# Audit & Login History
# ---------------------------

def create_audit_log(
    *,
    user=None,
    action,
    description="",
    status="SUCCESS",
    request=None,
    obj=None,
    company=None,
    branch=None,
):
    if company is None:
        company = getattr(user, "company", None) if user else None
    if branch is None:
        branch = getattr(user, "branch", None) if user else None

    ip_address = None
    user_agent = ""
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    AuditLog.objects.create(
        user=user,
        company=company,
        branch=branch,
        action=action,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(obj.pk) if obj else None,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status,
    )



def record_login(request, user, successful=True, session=None, failure_reason=""):
    if user is None:
        return None

    ua = parse(request.META.get("HTTP_USER_AGENT", ""))

    LoginHistory.objects.create(
        user=user,
        company=getattr(user, "company", None),
        branch=getattr(user, "branch", None),
        session=session,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        browser=ua.browser.family,
        operating_system=ua.os.family,
        device=ua.device.family,
        successful=successful,
        failure_reason=failure_reason if not successful else "",
    )


def is_suspicious_login(session):
    """Return whether a session differs from the user's known session profile."""
    previous_sessions = ActiveSession.objects.filter(
        user=session.user,
    ).exclude(pk=session.pk)

    if not previous_sessions.exists():
        return False

    known_session = previous_sessions.order_by("-last_activity").first()
    return any(
        current and known
        for current, known in (
            (session.ip_address, known_session.ip_address),
            (session.browser, known_session.browser),
            (session.operating_system, known_session.operating_system),
            (session.device, known_session.device),
        )
        if current != known
    )


def create_active_session(request, user, refresh_jti, expires_at=None):
    ua = parse(request.META.get("HTTP_USER_AGENT", ""))

    session = ActiveSession.objects.create(
        user=user,
        company=getattr(user, "company", None),
        branch=getattr(user, "branch", None),
        refresh_token_jti=refresh_jti,
        ip_address=get_client_ip(request),
        browser=ua.browser.family,
        operating_system=ua.os.family,
        device=ua.device.family,
        expires_at=expires_at,
    )


    if is_suspicious_login(session):
        CommunicationService.send(
            recipient=user,
            company=getattr(user, "company", None),
            notification_type="SECURITY",
            title="Security alert",
            message="A suspicious login was detected on your account.",
            reference_id=str(session.id),
            send_email=True,
            force_email=True,
            email_subject="Security alert",
            email_template="emails/security_alert.html",
            email_context={
                "security_message": f"Suspicious login detected from {ua.browser.family} on {ua.os.family} ({ua.device.family}) at {session.ip_address}.",
            },
        )


    # 🔔 Notify user about new login
    create_notification(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="NEW_LOGIN",
        title="New Login Detected",
        message=f"A new login was detected from {ua.browser.family} on {ua.os.family} ({ua.device.family}) at {session.ip_address}.",
        reference_id=str(session.id),
    )

    return session


# ---------------------------
# Failed Login Attempts
# ---------------------------

def is_account_locked(email, ip):
    attempt = FailedLoginAttempt.objects.filter(email=email, ip_address=ip).first()
    return bool(attempt and attempt.locked_until and attempt.locked_until > timezone.now())


def register_failed_attempt(email, ip, reason="Invalid credentials"):
    attempt, _ = FailedLoginAttempt.objects.get_or_create(email=email, ip_address=ip)
    attempt.attempts += 1
    attempt.reason = reason
    attempt.last_attempt_at = timezone.now()

    if attempt.attempts >= MAX_LOGIN_ATTEMPTS:
        attempt.locked_until = timezone.now() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
        attempt.save()

        # 🔔 Notify user about account lock
        try:
            user = User.objects.get(email=email)

            # In-app notification
            create_notification(
                recipient=user,
                company=getattr(user, "company", None),
                notification_type="ACCOUNT_LOCKED",
                title="Account Locked",
                message=f"Your account has been locked due to too many failed login attempts from IP {ip}.",
                reference_id=str(user.id),
            )

            # Security email (forced)
            CommunicationService.send(
                recipient=user,
                company=getattr(user, "company", None),
                notification_type="SECURITY",
                title="Security alert",
                message="Your account was locked due to multiple failed login attempts.",
                reference_id=str(user.id),
                send_email=True,
                force_email=True,  # bypass preferences
                email_subject="Security alert",
                email_template="emails/security_alert.html",
                email_context={
                    "security_message": f"Your account was locked after failed login attempts from IP {ip}.",
                },
            )
        except User.DoesNotExist:
            pass

    else:
        attempt.save()
    return attempt


def clear_failed_attempts(email, ip):
    FailedLoginAttempt.objects.filter(email=email, ip_address=ip).delete()


# ---------------------------
# OTP (2FA)
# ---------------------------

def generate_otp(user, fingerprint):
    code = f"{secrets.randbelow(1_000_000):06d}"
    otp = OTP.objects.create(
        user=user,
        code=code,
        fingerprint=fingerprint,
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )

    # Security email (forced)
    CommunicationService.send(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title="Security alert",
        message="Your one-time password (OTP) was generated for login.",
        reference_id=str(otp.id),
        send_email=True,
        force_email=True,  # bypass preferences
        email_subject="Your Login OTP",
        email_template="emails/security_alert.html",
        email_context={
            "security_message": f"Your OTP code is {code}. It will expire in 5 minutes.",
        },
    )

    return otp




def verify_otp(user, code, fingerprint):
    otp = OTP.objects.filter(
        user=user,
        code=code,
        fingerprint=fingerprint,
        is_used=False
    ).first()

    if otp and otp.is_valid():
        otp.is_used = True
        otp.save()

        # 🔔 Notify user about successful OTP verification
        create_notification(
            recipient=user,
            company=getattr(user, "company", None),
            notification_type="OTP_SUCCESS",
            title="OTP Verified",
            message="Your OTP was successfully verified. Login completed securely.",
            reference_id=str(user.id),
        )

        # Optional: notify admins for visibility
        if hasattr(user, "company"):
            admins = user.company.users.filter(role="ADMIN").exclude(id=user.id)
            for admin in admins:
                create_notification(
                    recipient=admin,
                    company=user.company,
                    notification_type="OTP_SUCCESS",
                    title="User OTP Verified",
                    message=f"User {user.get_full_name()} successfully verified their OTP.",
                    reference_id=str(user.id),
                )

        return True
    else:
        # 🔔 Notify user about failed OTP attempt
        create_notification(
            recipient=user,
            company=getattr(user, "company", None),
            notification_type="OTP_FAILED",
            title="Failed OTP Attempt",
            message="There was a failed OTP verification attempt on your account. If this wasn't you, please secure your account immediately.",
            reference_id=str(user.id),
        )

        # Security email (forced)
        CommunicationService.send(
            recipient=user,
            company=getattr(user, "company", None),
            notification_type="SECURITY",
            title="Security alert",
            message="A failed OTP attempt was detected on your account.",
            reference_id=str(user.id),
            send_email=True,
            force_email=True,  # bypass preferences
            email_subject="Security alert",
            email_template="emails/security_alert.html",
            email_context={
                "security_message": "There was a failed OTP verification attempt. If this wasn't you, please reset your password and review your security settings immediately.",
            },
        )
        # Optional: notify admins for visibility
        if hasattr(user, "company"):
            admins = user.company.users.filter(role="ADMIN").exclude(id=user.id)
            for admin in admins:
                create_notification(
                    recipient=admin,
                    company=user.company,
                    notification_type="OTP_FAILED",
                    title="User OTP Failure",
                    message=f"User {user.get_full_name()} had a failed OTP attempt.",
                    reference_id=str(user.id),
                )

        return False




def handle_expired_otps():
    """Mark expired OTPs and notify users/admins."""
    now = timezone.now()
    expired_otps = OTP.objects.filter(is_used=False, expires_at__lt=now)

    for otp in expired_otps:
        otp.is_used = True  # mark as consumed/invalid
        otp.save()

        # 🔔 Notify user about expired OTP
        create_notification(
            recipient=otp.user,
            company=getattr(otp.user, "company", None),
            notification_type="OTP_EXPIRED",
            title="OTP Expired",
            message="Your OTP expired without being used. Please request a new one to continue login.",
            reference_id=str(otp.user.id),
        )

        # Optional: notify admins for visibility
        if hasattr(otp.user, "company"):
            admins = otp.user.company.users.filter(role="ADMIN").exclude(id=otp.user.id)
            for admin in admins:
                create_notification(
                    recipient=admin,
                    company=otp.user.company,
                    notification_type="OTP_EXPIRED",
                    title="User OTP Expired",
                    message=f"User {otp.user.get_full_name()} had an OTP expire unused.",
                    reference_id=str(otp.user.id),
                )


def update_mfa_settings(user, enabled, request=None):
    # Update MFA flag
    user.mfa_enabled = enabled
    user.save()

    # Audit log
    create_audit_log(
        user=user,
        action="MFA_CHANGED",
        description=f"MFA {'enabled' if enabled else 'disabled'}",
        request=request,
    )

    # ✅ Security email (forced)
    CommunicationService.send(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title="Security alert",
        message="Your multi-factor authentication settings were updated.",
        reference_id=str(user.id),
        send_email=True,
        force_email=True,  # bypass preferences
        email_subject="Security alert",
        email_template="emails/security_alert.html",
        email_context={
            "security_message": (
                "MFA was "
                + ("enabled" if enabled else "disabled")
                + " on your account. If this wasn't you, please secure your account immediately."
            ),
        },
    )

    return True



def force_logout(user, reason="Admin intervention", request=None):
    # End all active sessions
    ActiveSession.objects.filter(user=user).delete()

    # Audit log
    create_audit_log(
        user=user,
        action="FORCED_LOGOUT",
        description=reason,
        request=request,
    )

    # In-app notification
    create_notification(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="ACCOUNT_INTERVENTION",
        title="Account Intervention",
        message=f"Your account was logged out due to: {reason}.",
        reference_id=str(user.id),
    )

    # Security email (forced)
    CommunicationService.send(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title="Security alert",
        message="Your account was logged out due to an intervention.",
        reference_id=str(user.id),
        send_email=True,
        force_email=True,  # bypass preferences
        email_subject="Security alert",
        email_template="emails/security_alert.html",
        email_context={
            "security_message": f"Your account was logged out due to: {reason}. If this wasn't expected, please contact support immediately.",
        },
    )

    


def change_password(user, new_password, request=None):
    # Update password
    user.set_password(new_password)
    user.save()

    # Audit log
    create_audit_log(
        user=user,
        action="PASSWORD_CHANGED",
        description="User changed their password",
        request=request,
    )

    # Security email (forced)
    CommunicationService.send(
        recipient=user,
        company=getattr(user, "company", None),
        notification_type="SECURITY",
        title="Security alert",
        message="Your password has been changed.",
        reference_id=str(user.id),
        send_email=True,
        force_email=True,  # bypass preferences
        email_subject="Security alert",
        email_template="emails/security_alert.html",
        email_context={
            "security_message": "Your password was successfully changed. If this wasn't you, please reset your password immediately.",
        },
    )

    return True

