from email.utils import formataddr, parseaddr

from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.html import escape

import logging

logger = logging.getLogger(__name__)

# ✅ Single shared instance
password_reset_token = PasswordResetTokenGenerator()


def send_invitation_email(invite):
    company = invite.company
    inviter_name = invite.created_by.full_name if invite.created_by else "A company administrator"
    invitation_link = f"{settings.FRONTEND_URL}/invitations/{invite.token}/"
    reply_to = [company.email] if company.email else None

    subject = f"Invitation to join {company.name}"
    text_message = (
        f"You have been invited to join {company.name}.\n\n"
        f"Invited by: {inviter_name}\n"
        f"Role: {invite.get_role_display()}\n"
        f"Invitation expires: {invite.expires_at:%Y-%m-%d %H:%M} UTC\n\n"
        f"Accept invitation: {invitation_link}\n\n"
        "If you were not expecting this invitation, contact your company administrator."
    )
    html_message = f"""
    <html>
      <body style="font-family:Arial,sans-serif;background:#f9f9f9;padding:20px;">
        <div style="max-width:600px;margin:auto;background:#fff;padding:20px;border-radius:8px;">
          <h2>Invitation to join {escape(company.name)}</h2>
          <p>You have been invited to join <strong>{escape(company.name)}</strong>.</p>
          <p>Invited by: {escape(inviter_name)}</p>
          <p>Role: {escape(invite.get_role_display())}</p>
          <p>Invitation expires: {invite.expires_at:%Y-%m-%d %H:%M} UTC</p>
          <p style="text-align:center;">
            <a href="{escape(invitation_link)}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;">
              Accept invitation
            </a>
          </p>
          <p>If you were not expecting this invitation, contact your company administrator.</p>
        </div>
      </body>
    </html>
    """

    try:
        _, from_address = parseaddr(settings.DEFAULT_FROM_EMAIL)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=formataddr(
                (
                    f"{company.name} via Business Management System",
                    from_address,
                )
            ),
            to=[invite.email],
            reply_to=reply_to,
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        logger.info("Invitation email sent to %s for company %s", invite.email, company.pk)
        return True
    except Exception:
        logger.exception("Invitation email failed for %s", invite.email)
        return False


def send_verification_email(user, token):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{settings.FRONTEND_URL}/verify-email/?uid={uidb64}&token={token}"

    subject = "[SmartBiz AI] Verify your account"

    text_message = (
        "Welcome to SmartBiz AI!\n\n"
        f"Verify your account:\n{link}\n\n"
        "If you didn’t create this account, ignore this email."
    )

    html_message = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f9f9f9; padding:20px;">
        <div style="max-width:600px;margin:auto;background:#fff;padding:20px;border-radius:8px;">
          <h2>Welcome to SmartBiz AI</h2>
          <p>Please confirm your email:</p>
          <p style="text-align:center;">
            <a href="{link}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;">
              Verify Email
            </a>
          </p>
        </div>
      </body>
    </html>
    """

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
        logger.info(f"Verification email sent to {user.email}")
    except Exception as e:
        logger.error(f"Verification email failed for {user.email}: {e}")


def send_password_reset_email(user, uidb64, token):
    link = f"{settings.FRONTEND_URL}/reset-password/?uid={uidb64}&token={token}"

    subject = "[SmartBiz AI] Reset your password"

    text_message = (
        f"Reset your password:\n{link}\n\n"
        "If you didn’t request this, ignore this email."
    )

    html_message = f"""
    <html>
      <body style="font-family: Arial; background:#f9f9f9; padding:20px;">
        <div style="max-width:600px;margin:auto;background:#fff;padding:20px;border-radius:8px;">
          <h2>Reset Password</h2>
          <p>Click below to reset your password:</p>
          <p style="text-align:center;">
            <a href="{link}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;">
              Reset Password
            </a>
          </p>
        </div>
      </body>
    </html>
    """

    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
        logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logger.error(f"Password reset email failed for {user.email}: {e}")