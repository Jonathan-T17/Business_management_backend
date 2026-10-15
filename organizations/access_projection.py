"""In-memory profile snapshots for access previews; no model is saved."""
from copy import copy
from .models import EmployeePositionAssignment
from .access_summary import employee_access_summary


def profile_snapshot(profile):
    projected = copy(profile)
    actor = copy(profile.user)
    projected.user = actor
    actor.employee_profile = projected
    return projected


def active_assignments(profile):
    return list(EmployeePositionAssignment.objects.filter(
        company_id=profile.company_id, employee=profile, is_active=True,
        position__company_id=profile.company_id, position__is_active=True,
    ).select_related('position').prefetch_related('branches', 'position__capability_grants'))


def primary_position_projection(profile, position):
    projected = profile_snapshot(profile)
    if not profile.position_id and position.branch_id:
        projected.branch = position.branch
        projected.user.branch = position.branch
    projected.position = position
    # Invitation access unlocks on an active primary position. The live account
    # retains its flag; this snapshot evaluates the proposed state only.
    if projected.status == 'ACTIVE' and position.is_active:
        projected.user.position_required = False
    assignments = [item for item in active_assignments(profile) if item.position_id != position.pk]
    return employee_access_summary(projected, projected_assignments=assignments)


def position_access_projection(profile, position, capabilities, scope):
    projected = profile_snapshot(profile)
    replacement = copy(position)
    replacement.primary_scope = scope
    if projected.position_id == position.pk:
        projected.position = replacement
    assignments = [item for item in active_assignments(profile) if item.position_id != projected.position_id]
    return employee_access_summary(projected, projected_assignments=assignments,
                                   capability_overrides={position.pk: capabilities})
