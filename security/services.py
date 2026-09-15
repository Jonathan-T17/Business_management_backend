import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from core.authorization import Authorization
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from .models import ActiveSession, AuditLog, FailedLoginAttempt, LoginHistory, OTP, SupportAccessSession, TrustedDevice
from .utils import get_client_ip
from user_agents import parse

MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15
OTP_TTL_MINUTES = 5
OTP_MAX_PER_15_MINUTES = 5
SAFE_SUPPORT_SCOPES = {
    "COMPANY_CONFIGURATION", "ORGANIZATION_CONFIGURATION", "WORKFLOW_CONFIGURATION",
    "REPORTING_CONFIGURATION", "SUBSCRIPTION_DIAGNOSTICS", "SECURITY_DIAGNOSTICS",
}
PROHIBITED_SUPPORT_SCOPES = {
    "COMPENSATION", "HR_CONFIDENTIAL", "PRIVATE_CHAT", "PRECISE_LOCATION",
    "PRIVATE_DOCUMENTS", "SENSITIVE_FORM_DATA", "OFFICIAL_RECORD_SNAPSHOTS",
}


def _hash_principal(email):
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def record_login(request, user, successful=True, session=None, failure_reason=""):
    if user is None:
        return None
    ua = parse(request.META.get("HTTP_USER_AGENT", ""))
    return LoginHistory.objects.create(
        user=user, company=user.company, branch=user.branch, session=session,
        email_hash=_hash_principal(user.email), ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        browser=ua.browser.family, operating_system=ua.os.family, device=ua.device.family,
        successful=successful, failure_reason=failure_reason[:255] if not successful else "",
    )


def create_active_session(request, user, refresh_jti, expires_at=None):
    ua = parse(request.META.get("HTTP_USER_AGENT", ""))
    if expires_at is None:
        token = OutstandingToken.objects.filter(jti=refresh_jti, user=user).first()
        expires_at = token.expires_at if token else timezone.now() + settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return ActiveSession.objects.create(
        user=user, company=user.company, branch=user.branch,
        refresh_token_jti=refresh_jti, ip_address=get_client_ip(request),
        browser=ua.browser.family, operating_system=ua.os.family,
        device=ua.device.family, expires_at=expires_at,
    )


def create_audit_log(*, user=None, action, request=None, company=None, branch=None, description="", status="SUCCESS", severity="INFO", actor_type=None, obj=None, metadata=None):
    if user and company is None:
        company = getattr(user, "company", None)
    if user and branch is None:
        branch = getattr(user, "branch", None)
    if actor_type is None:
        actor_type = "PLATFORM" if user and Authorization.is_platform_superuser(user) else ("USER" if user else "SYSTEM")
    return AuditLog.objects.create(
        user=user,
        company=company,
        branch=branch,
        action=action,
        severity=severity,
        actor_type=actor_type,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(obj.pk) if obj and getattr(obj, "pk", None) else None,
        description=description[:2000],
        metadata=metadata or {},
        ip_address=getattr(request, "client_ip", None) or (request.META.get("REMOTE_ADDR") if request else None),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:1000] if request else ""),
        status=status,
    )


def blacklist_refresh_jti(jti):
    if not jti:
        return
    token = OutstandingToken.objects.filter(jti=jti).first()
    if token:
        BlacklistedToken.objects.get_or_create(token=token)


@transaction.atomic
def terminate_session(*, session, actor=None, reason="SECURITY", note="", request=None):
    session = ActiveSession.objects.select_for_update().get(pk=session.pk)
    if session.is_active:
        session.is_active = False
        session.terminated_at = timezone.now()
        session.terminated_by = actor
        session.termination_reason = reason
        session.termination_note = note[:500]
        session.save(update_fields=["is_active", "terminated_at", "terminated_by", "termination_reason", "termination_note"])
        blacklist_refresh_jti(session.refresh_token_jti)
    create_audit_log(user=actor, company=session.company, branch=session.branch, request=request, action="SESSION_TERMINATED", severity="WARNING", description="Session terminated.", obj=session, metadata={"reason": reason})
    return session


@transaction.atomic
def terminate_user_sessions(user, *, actor=None, reason="ACCOUNT_STATE", note="", request=None):
    sessions = list(ActiveSession.objects.select_for_update().filter(user=user, is_active=True))
    for session in sessions:
        terminate_session(session=session, actor=actor, reason=reason, note=note, request=request)
    return len(sessions)


@transaction.atomic
def terminate_company_sessions(company, *, actor=None, reason="SECURITY", note="", request=None):
    sessions = list(ActiveSession.objects.select_for_update().filter(company=company, is_active=True))
    for session in sessions:
        terminate_session(session=session, actor=actor, reason=reason, note=note, request=request)
    return len(sessions)


def is_account_locked(email, ip):
    row = FailedLoginAttempt.objects.filter(email_hash=_hash_principal(email), ip_address=ip).first()
    return bool(row and row.locked_until and row.locked_until > timezone.now())


@transaction.atomic
def register_failed_attempt(email, ip, reason="Invalid credentials"):
    email_hash = _hash_principal(email)
    row, _ = FailedLoginAttempt.objects.select_for_update().get_or_create(
        email_hash=email_hash,
        ip_address=ip,
        defaults={"email_hint": email[:2] + "***" if email else ""},
    )
    row.attempts += 1
    row.reason = reason[:255]
    if row.attempts >= MAX_LOGIN_ATTEMPTS:
        row.locked_until = timezone.now() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
    row.save()
    return row


def clear_failed_attempts(email, ip):
    FailedLoginAttempt.objects.filter(email_hash=_hash_principal(email), ip_address=ip).update(attempts=0, locked_until=None)


@transaction.atomic
def generate_otp(user, device_token_hash=""):
    cutoff = timezone.now() - timedelta(minutes=15)
    if OTP.objects.filter(user=user, created_at__gte=cutoff).count() >= OTP_MAX_PER_15_MINUTES:
        raise ValidationError("Too many verification requests. Try again later.")
    OTP.objects.filter(user=user, purpose=OTP.PURPOSE_LOGIN, used_at__isnull=True, invalidated_at__isnull=True).update(invalidated_at=timezone.now())
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OTP.objects.create(
        user=user,
        code_digest=OTP.digest(code),
        device_token_hash=device_token_hash,
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    return challenge, code


@transaction.atomic
def verify_otp(user, *, challenge_id, code, device_token_hash=""):
    if not Authorization.can_authenticate(user):
        return False
    challenge = OTP.objects.select_for_update().filter(challenge_id=challenge_id, user=user, purpose=OTP.PURPOSE_LOGIN).first()
    if not challenge or not challenge.is_active:
        return False
    if challenge.device_token_hash and challenge.device_token_hash != device_token_hash:
        return False
    challenge.attempts += 1
    if challenge.matches(code):
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["attempts", "used_at"])
        return True
    if challenge.attempts >= challenge.max_attempts:
        challenge.invalidated_at = timezone.now()
    challenge.save(update_fields=["attempts", "invalidated_at"])
    return False


def trusted_device_hash(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_trusted_device_token():
    raw = secrets.token_urlsafe(48)
    return raw, trusted_device_hash(raw)


class SupportAccessService:
    @classmethod
    @transaction.atomic
    def request(cls, *, company, support_agent, reason, scopes, expires_at, ticket=None, request=None):
        if not CapabilityService.has(support_agent, Capabilities.PLATFORM_SUPPORT):
            raise PermissionDenied("Platform support authority is required.")
        scopes = set(scopes or [])
        if not scopes or scopes - SAFE_SUPPORT_SCOPES or scopes & PROHIBITED_SUPPORT_SCOPES:
            raise ValidationError("One or more support-access scopes are not permitted.")
        if expires_at <= timezone.now() or expires_at > timezone.now() + timedelta(hours=4):
            raise ValidationError("Support access must expire within four hours.")
        obj = SupportAccessSession.objects.create(company=company, support_agent=support_agent, ticket=ticket, reason=reason, scopes=sorted(scopes), expires_at=expires_at)
        create_audit_log(user=support_agent, company=company, request=request, action="SUPPORT_ACCESS_REQUESTED", severity="WARNING", actor_type="SUPPORT", description="Temporary tenant support access requested.", obj=obj, metadata={"scopes": sorted(scopes), "ticket": str(ticket.pk) if ticket else None})
        return obj

    @classmethod
    @transaction.atomic
    def approve(cls, *, access_session, approver, request=None):
        if not CapabilityService.has(approver, Capabilities.PLATFORM_ADMIN):
            raise PermissionDenied("Platform administrator approval is required.")
        obj = SupportAccessSession.objects.select_for_update().get(pk=access_session.pk)
        if obj.status != "PENDING" or obj.expires_at <= timezone.now():
            raise ValidationError("Support access request is no longer approvable.")
        if obj.support_agent_id == approver.id:
            raise ValidationError("Support access requires a different approver.")
        obj.status = "ACTIVE"
        obj.approved_by = approver
        obj.approved_at = timezone.now()
        obj.starts_at = timezone.now()
        obj.save(update_fields=["status", "approved_by", "approved_at", "starts_at"])
        create_audit_log(user=approver, company=obj.company, request=request, action="SUPPORT_ACCESS_APPROVED", severity="CRITICAL", actor_type="PLATFORM", description="Temporary tenant support access approved.", obj=obj, metadata={"scopes": obj.scopes})
        return obj

    @classmethod
    @transaction.atomic
    def end(cls, *, access_session, actor, reason="", request=None):
        obj = SupportAccessSession.objects.select_for_update().get(pk=access_session.pk)
        if obj.status == "ACTIVE":
            obj.status = "ENDED"
            obj.ended_at = timezone.now()
            obj.end_reason = reason[:500]
            obj.save(update_fields=["status", "ended_at", "end_reason"])
        create_audit_log(user=actor, company=obj.company, request=request, action="SUPPORT_ACCESS_ENDED", severity="WARNING", actor_type="SUPPORT", description="Temporary tenant support access ended.", obj=obj)
        return obj

    @classmethod
    def active_for(cls, *, support_agent, company, required_scope):
        return SupportAccessSession.objects.filter(
            support_agent=support_agent, company=company, status="ACTIVE",
            starts_at__lte=timezone.now(), expires_at__gt=timezone.now(), scopes__contains=[required_scope],
        ).exists()





# from django.utils import timezone
# from datetime import timedelta
# import secrets
# from django.core.mail import send_mail
# from user_agents import parse

# from notifications.services import CommunicationService, create_notification
# from users.models import User

# from .models import LoginHistory, AuditLog, ActiveSession, FailedLoginAttempt, OTP
# from .constants import MAX_LOGIN_ATTEMPTS, ACCOUNT_LOCK_MINUTES
# from .utils import get_client_ip
# from core.authorization import Authorization


# def terminate_user_sessions(user, reason="Account access revoked"):
#     """Invalidate every active session for a user during offboarding."""
#     return ActiveSession.objects.filter(
#         user=user,
#         is_active=True,
#     ).update(
#         is_active=False,
#         terminated_at=timezone.now(),
#     )


# def terminate_company_sessions(company, reason="Company access revoked"):
#     """Invalidate every active session belonging to a company."""
#     return ActiveSession.objects.filter(
#         company=company,
#         is_active=True,
#     ).update(
#         is_active=False,
#         terminated_at=timezone.now(),
#     )


# # ---------------------------
# # Audit & Login History
# # ---------------------------

# def create_audit_log(
#     *,
#     user=None,
#     action,
#     description="",
#     status="SUCCESS",
#     request=None,
#     obj=None,
#     company=None,
#     branch=None,
# ):
#     if company is None:
#         company = getattr(user, "company", None) if user else None
#     if branch is None:
#         branch = getattr(user, "branch", None) if user else None

#     ip_address = None
#     user_agent = ""
#     if request:
#         ip_address = get_client_ip(request)
#         user_agent = request.META.get("HTTP_USER_AGENT", "")

#     AuditLog.objects.create(
#         user=user,
#         company=company,
#         branch=branch,
#         action=action,
#         object_type=obj.__class__.__name__ if obj else "",
#         object_id=str(obj.pk) if obj else None,
#         description=description,
#         ip_address=ip_address,
#         user_agent=user_agent,
#         status=status,
#     )



# def record_login(request, user, successful=True, session=None, failure_reason=""):
#     if user is None:
#         return None

#     ua = parse(request.META.get("HTTP_USER_AGENT", ""))

#     LoginHistory.objects.create(
#         user=user,
#         company=getattr(user, "company", None),
#         branch=getattr(user, "branch", None),
#         session=session,
#         ip_address=get_client_ip(request),
#         user_agent=request.META.get("HTTP_USER_AGENT", ""),
#         browser=ua.browser.family,
#         operating_system=ua.os.family,
#         device=ua.device.family,
#         successful=successful,
#         failure_reason=failure_reason if not successful else "",
#     )


# def is_suspicious_login(session):
#     """Return whether a session differs from the user's known session profile."""
#     previous_sessions = ActiveSession.objects.filter(
#         user=session.user,
#     ).exclude(pk=session.pk)

#     if not previous_sessions.exists():
#         return False

#     known_session = previous_sessions.order_by("-last_activity").first()
#     return any(
#         current and known
#         for current, known in (
#             (session.ip_address, known_session.ip_address),
#             (session.browser, known_session.browser),
#             (session.operating_system, known_session.operating_system),
#             (session.device, known_session.device),
#         )
#         if current != known
#     )


# def create_active_session(request, user, refresh_jti, expires_at=None):
#     ua = parse(request.META.get("HTTP_USER_AGENT", ""))

#     session = ActiveSession.objects.create(
#         user=user,
#         company=getattr(user, "company", None),
#         branch=getattr(user, "branch", None),
#         refresh_token_jti=refresh_jti,
#         ip_address=get_client_ip(request),
#         browser=ua.browser.family,
#         operating_system=ua.os.family,
#         device=ua.device.family,
#         expires_at=expires_at,
#     )


#     if is_suspicious_login(session):
#         CommunicationService.send(
#             recipient=user,
#             company=getattr(user, "company", None),
#             notification_type="SECURITY",
#             title="Security alert",
#             message="A suspicious login was detected on your account.",
#             reference_id=str(session.id),
#             send_email=True,
#             force_email=True,
#             email_subject="Security alert",
#             email_template="emails/security_alert.html",
#             email_context={
#                 "security_message": f"Suspicious login detected from {ua.browser.family} on {ua.os.family} ({ua.device.family}) at {session.ip_address}.",
#             },
#         )


#     # 🔔 Notify user about new login
#     create_notification(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="NEW_LOGIN",
#         title="New Login Detected",
#         message=f"A new login was detected from {ua.browser.family} on {ua.os.family} ({ua.device.family}) at {session.ip_address}.",
#         reference_id=str(session.id),
#     )

#     return session


# # ---------------------------
# # Failed Login Attempts
# # ---------------------------

# def is_account_locked(email, ip):
#     attempt = FailedLoginAttempt.objects.filter(email=email, ip_address=ip).first()
#     return bool(attempt and attempt.locked_until and attempt.locked_until > timezone.now())


# def register_failed_attempt(email, ip, reason="Invalid credentials"):
#     attempt, _ = FailedLoginAttempt.objects.get_or_create(email=email, ip_address=ip)
#     attempt.attempts += 1
#     attempt.reason = reason
#     attempt.last_attempt_at = timezone.now()

#     if attempt.attempts >= MAX_LOGIN_ATTEMPTS:
#         attempt.locked_until = timezone.now() + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
#         attempt.save()

#         # 🔔 Notify user about account lock
#         try:
#             user = User.objects.get(email=email)

#             # In-app notification
#             create_notification(
#                 recipient=user,
#                 company=getattr(user, "company", None),
#                 notification_type="ACCOUNT_LOCKED",
#                 title="Account Locked",
#                 message=f"Your account has been locked due to too many failed login attempts from IP {ip}.",
#                 reference_id=str(user.id),
#             )

#             # Security email (forced)
#             CommunicationService.send(
#                 recipient=user,
#                 company=getattr(user, "company", None),
#                 notification_type="SECURITY",
#                 title="Security alert",
#                 message="Your account was locked due to multiple failed login attempts.",
#                 reference_id=str(user.id),
#                 send_email=True,
#                 force_email=True,  # bypass preferences
#                 email_subject="Security alert",
#                 email_template="emails/security_alert.html",
#                 email_context={
#                     "security_message": f"Your account was locked after failed login attempts from IP {ip}.",
#                 },
#             )
#         except User.DoesNotExist:
#             pass

#     else:
#         attempt.save()
#     return attempt


# def clear_failed_attempts(email, ip):
#     FailedLoginAttempt.objects.filter(email=email, ip_address=ip).delete()


# # ---------------------------
# # OTP (2FA)
# # ---------------------------

# def generate_otp(user, fingerprint):
#     code = f"{secrets.randbelow(1_000_000):06d}"
#     otp = OTP.objects.create(
#         user=user,
#         code=code,
#         fingerprint=fingerprint,
#         expires_at=timezone.now() + timezone.timedelta(minutes=5),
#     )

#     # Security email (forced)
#     CommunicationService.send(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="OTP_DELIVERY",
#         title="Security alert",
#         message="Your one-time password (OTP) was generated for login.",
#         reference_id=str(otp.id),
#         send_email=True,
#         force_email=True,  # bypass preferences
#         email_subject="Your Login OTP",
#         email_template="emails/security_alert.html",
#         email_context={
#             "security_message": f"Your OTP code is {code}. It will expire in 5 minutes.",
#         },
#     )

#     return otp




# def verify_otp(user, code, fingerprint):
#     if not Authorization.can_authenticate(user):
#         return False

#     otp = OTP.objects.filter(
#         user=user,
#         code=code,
#         fingerprint=fingerprint,
#         is_used=False
#     ).first()

#     if otp and otp.is_valid():
#         otp.is_used = True
#         otp.save()

#         # 🔔 Notify user about successful OTP verification
#         create_notification(
#             recipient=user,
#             company=getattr(user, "company", None),
#             notification_type="OTP_SUCCESS",
#             title="OTP Verified",
#             message="Your OTP was successfully verified. Login completed securely.",
#             reference_id=str(user.id),
#         )

#         return True
#     else:
#         # 🔔 Notify user about failed OTP attempt
#         create_notification(
#             recipient=user,
#             company=getattr(user, "company", None),
#             notification_type="OTP_FAILED",
#             title="Failed OTP Attempt",
#             message="There was a failed OTP verification attempt on your account. If this wasn't you, please secure your account immediately.",
#             reference_id=str(user.id),
#         )

#         # Security email (forced)
#         CommunicationService.send(
#             recipient=user,
#             company=getattr(user, "company", None),
#             notification_type="SECURITY",
#             title="Security alert",
#             message="A failed OTP attempt was detected on your account.",
#             reference_id=str(user.id),
#             send_email=True,
#             force_email=True,  # bypass preferences
#             email_subject="Security alert",
#             email_template="emails/security_alert.html",
#             email_context={
#                 "security_message": "There was a failed OTP verification attempt. If this wasn't you, please reset your password and review your security settings immediately.",
#             },
#         )
#         return False




# def handle_expired_otps():
#     """Mark expired OTPs and notify users/admins."""
#     now = timezone.now()
#     expired_otps = OTP.objects.filter(is_used=False, expires_at__lt=now)

#     for otp in expired_otps:
#         otp.is_used = True  # mark as consumed/invalid
#         otp.save()

#         # 🔔 Notify user about expired OTP
#         create_notification(
#             recipient=otp.user,
#             company=getattr(otp.user, "company", None),
#             notification_type="OTP_EXPIRED",
#             title="OTP Expired",
#             message="Your OTP expired without being used. Please request a new one to continue login.",
#             reference_id=str(otp.user.id),
#         )


# def update_mfa_settings(user, enabled, request=None):
#     # Update MFA flag
#     user.mfa_enabled = enabled
#     user.save()

#     # Audit log
#     create_audit_log(
#         user=user,
#         action="MFA_CHANGED",
#         description=f"MFA {'enabled' if enabled else 'disabled'}",
#         request=request,
#     )

#     # ✅ Security email (forced)
#     CommunicationService.send(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="SECURITY",
#         title="Security alert",
#         message="Your multi-factor authentication settings were updated.",
#         reference_id=str(user.id),
#         send_email=True,
#         force_email=True,  # bypass preferences
#         email_subject="Security alert",
#         email_template="emails/security_alert.html",
#         email_context={
#             "security_message": (
#                 "MFA was "
#                 + ("enabled" if enabled else "disabled")
#                 + " on your account. If this wasn't you, please secure your account immediately."
#             ),
#         },
#     )

#     return True



# def force_logout(user, reason="Admin intervention", request=None):
#     # End all active sessions
#     ActiveSession.objects.filter(user=user).delete()

#     # Audit log
#     create_audit_log(
#         user=user,
#         action="FORCED_LOGOUT",
#         description=reason,
#         request=request,
#     )

#     # In-app notification
#     create_notification(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="ACCOUNT_INTERVENTION",
#         title="Account Intervention",
#         message=f"Your account was logged out due to: {reason}.",
#         reference_id=str(user.id),
#     )

#     # Security email (forced)
#     CommunicationService.send(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="SECURITY",
#         title="Security alert",
#         message="Your account was logged out due to an intervention.",
#         reference_id=str(user.id),
#         send_email=True,
#         force_email=True,  # bypass preferences
#         email_subject="Security alert",
#         email_template="emails/security_alert.html",
#         email_context={
#             "security_message": f"Your account was logged out due to: {reason}. If this wasn't expected, please contact support immediately.",
#         },
#     )

    


# def change_password(user, new_password, request=None):
#     # Update password
#     user.set_password(new_password)
#     user.save()

#     # Audit log
#     create_audit_log(
#         user=user,
#         action="PASSWORD_CHANGED",
#         description="User changed their password",
#         request=request,
#     )

#     # Security email (forced)
#     CommunicationService.send(
#         recipient=user,
#         company=getattr(user, "company", None),
#         notification_type="SECURITY",
#         title="Security alert",
#         message="Your password has been changed.",
#         reference_id=str(user.id),
#         send_email=True,
#         force_email=True,  # bypass preferences
#         email_subject="Security alert",
#         email_template="emails/security_alert.html",
#         email_context={
#             "security_message": "Your password was successfully changed. If this wasn't you, please reset your password immediately.",
#         },
#     )

#     return True

