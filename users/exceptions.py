from rest_framework.exceptions import APIException
from rest_framework.exceptions import PermissionDenied


class AccountAccessUnavailable(PermissionDenied):
    default_code = "account_access_unavailable"


def account_access_message(user):
    if user.is_deleted:
        return "This account is unavailable. Contact platform support."
    if not user.is_active:
        if user.account_state == "PENDING_VERIFICATION":
            return "Verify your email address before signing in. Use Resend verification if you need a new link."
        if user.account_state == "TERMINATED":
            return "Your access to this company has ended. Contact your company administrator."
        if user.account_state == "SUSPENDED":
            return "Your account is suspended. Contact your company administrator."
        return "Your account is deactivated. Contact your company administrator or platform support."
    company = user.company
    if company and company.archived_at:
        return "Your company workspace has been archived. Contact platform support about recovery."
    if company and not company.is_active:
        return "Your company workspace is suspended. Contact your company administrator or platform support."
    return "This account has no active company workspace. Contact platform support."


class VerificationEmailUnavailable(APIException):
    status_code = 503
    default_code = "verification_email_unavailable"
    default_detail = "We couldn't send your verification email. Please try signing in again shortly."
