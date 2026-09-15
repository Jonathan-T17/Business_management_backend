from rest_framework.exceptions import APIException


class VerificationEmailUnavailable(APIException):
    status_code = 503
    default_code = "verification_email_unavailable"
    default_detail = "We couldn't send your verification email. Please try signing in again shortly."
