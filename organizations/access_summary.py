"""Read-only explanations of the same capabilities used by authorization."""
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService as CS
from core.position_scope import PositionScope, BRANCH_CAPABILITIES
from forms_engine.access import FormAccess


def employee_access_summary(profile, *, projected_assignments=None, capability_overrides=None):
    user = profile.user
    enabled = user.is_active and not user.is_deleted and user.company.is_active
    effective = CS.all_for(user) if enabled else set()
    company_caps = CS._tenant_capabilities(user, company_only=True) if enabled else set()
    primary = PositionScope.primary_position(user)
    primary_caps = PositionScope.primary_capabilities(user)
    def position_caps(position):
        if capability_overrides is not None and position.pk in capability_overrides:
            return set(capability_overrides[position.pk])
        return {g.capability for g in position.capability_grants.all() if g.is_active and g.company_id == user.company_id}
    if primary and capability_overrides is not None:
        primary_caps = position_caps(primary)
        if primary.primary_scope == 'BRANCH':
            primary_caps &= BRANCH_CAPABILITIES
    direct = set(user.capability_grants.filter(company_id=user.company_id, is_active=True).values_list('capability', flat=True))
    assignments = list(PositionScope.assignments(user).select_related('position').prefetch_related('position__capability_grants', 'branches'))
    if projected_assignments is not None:
        from companies.invitation_access import awaiting_position
        assignments = projected_assignments if profile.status == 'ACTIVE' and enabled else []
        baseline = direct | primary_caps
        baseline_company = direct | (primary_caps if primary and primary.primary_scope == 'COMPANY' else set())
        if user.role == 'ADMIN':
            baseline |= C.PRESETS['COMPANY_ADMINISTRATOR']
            baseline_company |= C.PRESETS['COMPANY_ADMINISTRATOR']
        if FormAccess.default_member_access(user):
            baseline.add(C.USE_FORMS)
        for assignment in assignments:
            caps = position_caps(assignment.position)
            if assignment.scope == 'COMPANY':
                baseline |= caps
                baseline_company |= caps
            elif any(b.is_active and b.company_id == user.company_id for b in assignment.branches.all()):
                baseline |= caps & BRANCH_CAPABILITIES
        permitted = set(C.values()) - C.PLATFORM_ONLY
        effective = baseline & permitted if enabled and not awaiting_position(user) else set()
        company_caps = baseline_company & permitted if enabled and not awaiting_position(user) else set()
    from companies.models import Branch
    branches = dict(Branch.objects.filter(company_id=user.company_id, is_active=True).values_list('id', 'name'))
    actions = []
    for code in sorted(effective):
        sources = []
        if user.role == 'ADMIN' and code in C.PRESETS['COMPANY_ADMINISTRATOR']:
            sources.append('Company administrator account')
        if code in direct:
            sources.append('Direct permission')
        if primary and code in primary_caps:
            sources.append(f'Primary position: {primary.title}')
        for assignment in assignments:
            caps = position_caps(assignment.position)
            if code in caps and (assignment.scope == 'COMPANY' or code in BRANCH_CAPABILITIES):
                if assignment.scope == 'COMPANY' or any(branch.pk in branches for branch in assignment.branches.all()):
                    sources.append(f'Additional position: {assignment.position.title}')
        member = code == C.USE_FORMS and FormAccess.default_member_access(user)
        if member:
            sources.append('Company membership: published forms')
        if projected_assignments is None:
            ids = PositionScope.branches_for(user, code)
        else:
            ids = {primary.branch_id} if primary and primary.primary_scope == 'BRANCH' and code in primary_caps else set()
            for assignment in assignments:
                if assignment.scope == 'BRANCHES' and code in BRANCH_CAPABILITIES and code in position_caps(assignment.position):
                    ids.update(b.pk for b in assignment.branches.all() if b.is_active and b.company_id == user.company_id)
        if member:
            ids.add(primary.branch_id if primary and primary.primary_scope == 'BRANCH' and primary_caps & {C.USE_FORMS, C.SUBMIT_FORMS} else user.branch_id)
        actions.append({'code': code, 'sensitive': code in C.SENSITIVE,
                        'company_wide': code in company_caps,
                        'branches': [{'id': pk, 'name': branches[pk]} for pk in sorted(ids - {None}) if pk in branches],
                        'sources': sources})
    return {'employee': profile.pk, 'account_active': enabled, 'actions': actions}
