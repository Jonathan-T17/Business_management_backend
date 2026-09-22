"""Accepted employee invitations stay restricted until an active position is assigned."""
from rest_framework.exceptions import PermissionDenied


def awaiting_position(user):
    if not getattr(user, "company_id", None) or user.role not in {"EMPLOYEE", "MANAGER"}:
        return False
    from companies.models import CompanyInvite
    from organizations.models import EmployeeProfile
    invited = CompanyInvite.objects.filter(company_id=user.company_id, email__iexact=user.email,
        status="ACCEPTED", position__isnull=True).exists()
    if not invited:
        return False
    return not EmployeeProfile.objects.filter(user=user, company_id=user.company_id,
        status="ACTIVE", position__is_active=True, position__company_id=user.company_id).exists()


def enforce_invitation_access(request, user):
    path = request.path_info
    if not path.startswith("/api/v1/") or request.method == "OPTIONS":
        return
    resource = path.removeprefix("/api/v1/").split("/")[0]
    personal = {"profile", "token", "logout", "verify-otp", "password-reset", "confirm-password-reset", "trusted-devices"}
    if resource in personal or path.startswith("/api/v1/security/sessions/") or path.startswith("/api/v1/security/trusted-devices/") or path == "/api/v1/company-setup/access/":
        return
    if awaiting_position(user):
        raise PermissionDenied("Your company administrator needs to assign your position before you can access company information.", code="position_assignment_required")
