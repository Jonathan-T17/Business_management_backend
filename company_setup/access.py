"""Setup gates complement (and never replace) normal tenant permissions."""
from rest_framework.exceptions import PermissionDenied
from .models import CompanySetupState
from .setup_contract import SETUP_VERSION


class CompanySetupRequired(PermissionDenied):
    default_code = "company_setup_required"


def setup_required(user):
    from core.capability_service import CapabilityService
    return bool(
        CapabilityService.is_tenant_identity(user)
        and not CompanySetupState.objects.filter(
            company_id=user.company_id, onboarding_completed=True, setup_version=SETUP_VERSION
        ).exists()
    )


def enforce_setup_access(request, user):
    # Resolve the API resource, rather than trusting query parameters or UI state.
    path = request.path_info
    if not path.startswith('/api/v1/'):
        return
    resource = path.removeprefix('/api/v1/').split('/')[0]
    available_during_setup = {
        'auth', 'token', 'verify-otp', 'logout', 'register', 'verify-email',
        'resend-verification', 'password-reset', 'confirm-password-reset',
        'profile', 'users', 'security', 'trusted-devices',
        'company', 'companies', 'branches', 'invitations', 'invites', 'invite',
        'company-setup', 'organizations', 'departments', 'teams', 'employees',
        'positions', 'form-templates', 'reporting-schedules', 'workflow-definitions',
        'subscriptions', 'subscription', 'plans', 'notifications', 'support',
        'company-audit-logs', 'company-active-sessions',
    }
    if resource in available_during_setup or request.method == 'OPTIONS':
        return
    if setup_required(user):
        raise CompanySetupRequired(
            'Complete company setup before opening operational work. Go to the dashboard to continue.',
            code='company_setup_required',
        )
