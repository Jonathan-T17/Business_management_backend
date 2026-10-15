from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Branch, Company, CompanyInvite
from organizations.models import EmployeeProfile, Position, PositionCapabilityGrant, UserCapabilityGrant
from organizations.serializers import EmployeeProfileSerializer


@pytest.fixture
def directory_scope_fixture(django_user_model):
    home = Company.objects.create(name='Directory scope home')
    other = Company.objects.create(name='Directory scope other')
    north = Branch.objects.create(company=home, name='North')
    south = Branch.objects.create(company=home, name='South')
    empty = Branch.objects.create(company=home, name='Empty branch')
    admin = django_user_model.objects.create_user(email='dir-admin@test.local', company=home, role='ADMIN', is_active=True)
    manager = django_user_model.objects.create_user(email='dir-manager@test.local', company=home, branch=north, role='MANAGER', is_active=True)
    people = []
    for name, branch, status in [('North active', north, 'ACTIVE'), ('South leave', south, 'ON_LEAVE'), ('North terminated', north, 'TERMINATED')]:
        user = django_user_model.objects.create_user(email=name.replace(' ', '-')+'@test.local', full_name=name, company=home, branch=branch, role='EMPLOYEE', is_active=True)
        people.append(EmployeeProfile.objects.create(company=home, user=user, employee_id=name, branch=branch, status=status, phone='Private phone', emergency_contact='Private emergency', notes='Private HR note', termination_reason='Private reason'))
    outsider = django_user_model.objects.create_user(email='dir-outsider@test.local', company=other, role='EMPLOYEE', is_active=True)
    EmployeeProfile.objects.create(company=other, user=outsider, employee_id='Foreign')
    CompanyInvite.objects.create(company=home, email='pending@test.local', role='EMPLOYEE', expires_at=timezone.now()+timedelta(days=1))
    CompanyInvite.objects.create(company=home, email='expired@test.local', role='EMPLOYEE', expires_at=timezone.now()-timedelta(days=1))
    client = APIClient()
    return home, north, south, empty, admin, manager, people, outsider, client


@pytest.mark.django_db
def test_company_position_directory_access_matches_permission(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    actor = people[0].user
    position = Position.objects.create(company=home, title='Directory leader', primary_scope='COMPANY')
    PositionCapabilityGrant.objects.create(company=home, position=position, capability='VIEW_ALL_EMPLOYEES')
    people[0].position = position
    people[0].save()
    client.force_authenticate(actor)
    result = client.get('/api/v1/employees/')
    assert result.status_code == 200, result.data
    assert {row['id'] for row in result.data['results']} == {person.pk for person in people}
    assert all(not {'notes', 'emergency_contact', 'phone', 'termination_reason'} & row.keys() for row in result.data['results'])


@pytest.mark.django_db
def test_branch_permission_cannot_expand_directory_or_counts(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    actor = people[0].user
    position = Position.objects.create(company=home, branch=north, title='North directory', primary_scope='BRANCH')
    PositionCapabilityGrant.objects.create(company=home, position=position, capability='VIEW_ALL_EMPLOYEES')
    people[0].position = position
    people[0].save()
    client.force_authenticate(actor)
    result = client.get('/api/v1/employees/', {'branch': south.pk})
    assert result.status_code == 200 and result.data['count'] == 0
    overview = client.get('/api/v1/employees/overview/')
    assert overview.status_code == 200, overview.data
    assert overview.data['scope'] == 'BRANCHES'
    assert overview.data['total_profiles'] == 2
    assert overview.data['current_employees'] == 1
    assert {row['id'] for row in overview.data['branches']} == {north.pk}
    assert overview.data['workspace_accounts'] is None
    assert overview.data['pending_invitations'] is None


@pytest.mark.django_db
def test_company_headcounts_are_unpaginated_and_distinguish_accounts(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    result = client.get('/api/v1/employees/overview/', {'search': 'absent', 'page_size': 1})
    assert result.status_code == 200, result.data
    assert result.data['total_profiles'] == 3
    assert result.data['current_employees'] == 2
    assert result.data['active'] == 1
    assert result.data['on_leave'] == 1
    assert result.data['terminated'] == 1
    assert result.data['workspace_accounts'] == 5
    assert result.data['accounts_without_profile'] == 2
    assert result.data['pending_invitations'] == 1
    assert result.data['self_profile_id'] is None
    assert next(row for row in result.data['branches'] if row['id'] == empty.pk)['current'] == 0


@pytest.mark.django_db
def test_branch_and_status_filters_apply_before_pagination(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    result = client.get('/api/v1/employees/', {'branch': north.pk, 'status': 'ACTIVE', 'page_size': 1})
    assert result.status_code == 200, result.data
    assert result.data['count'] == 1
    assert result.data['results'][0]['id'] == people[0].pk


@pytest.mark.django_db
def test_manager_without_branch_has_no_unassigned_directory_access(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    people[1].branch = None
    people[1].save()
    manager.branch = None
    manager.save()
    client.force_authenticate(manager)
    result = client.get('/api/v1/employees/')
    assert result.status_code == 200 and result.data['count'] == 0


@pytest.mark.django_db
def test_directory_permission_does_not_grant_private_hr_data(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    result = client.get(f'/api/v1/employees/{people[0].pk}/')
    assert result.status_code == 200
    assert not {'notes', 'phone', 'emergency_contact', 'termination_reason', 'terminated_by'} & result.data.keys()
    for capability in ('VIEW_HR_CONFIDENTIAL', 'VIEW_PERSONAL_DATA'):
        UserCapabilityGrant.objects.create(company=home, user=admin, capability=capability)
    result = client.get(f'/api/v1/employees/{people[0].pk}/')
    assert result.data['notes'] == 'Private HR note'
    assert result.data['phone'] == 'Private phone'


@pytest.mark.django_db
def test_confidential_metadata_write_requires_explicit_access(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    serializer = EmployeeProfileSerializer(people[0], data={'notes': 'Change'}, partial=True, context={'request': SimpleNamespace(user=admin)})
    assert not serializer.is_valid() and 'notes' in serializer.errors


@pytest.mark.django_db
def test_view_only_directory_permission_cannot_change_employees(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    UserCapabilityGrant.objects.create(company=home, user=people[0].user, capability='VIEW_ALL_EMPLOYEES')
    client.force_authenticate(people[0].user)
    result = client.patch(f'/api/v1/employees/{people[1].pk}/', {'employee_id': 'Changed'}, format='json')
    assert result.status_code == 403
    people[1].refresh_from_db()
    assert people[1].employee_id != 'Changed'


@pytest.mark.django_db
def test_company_manage_permission_can_edit_without_an_admin_role(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    UserCapabilityGrant.objects.create(company=home, user=people[0].user, capability='MANAGE_EMPLOYEES')
    client.force_authenticate(people[0].user)
    result = client.patch(f'/api/v1/employees/{people[1].pk}/', {'employee_id': 'Authorized change'}, format='json')
    assert result.status_code == 200, result.data
    result = client.patch(f'/api/v1/employees/{EmployeeProfile.objects.get(user=outsider).pk}/', {'employee_id': 'Forbidden'}, format='json')
    assert result.status_code == 404


@pytest.mark.django_db
def test_admin_can_add_a_neutral_company_profile_without_granting_leadership(directory_scope_fixture):
    from core.capability_service import CapabilityService
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    capabilities_before = CapabilityService.all_for(admin)
    client.force_authenticate(admin)
    result = client.post('/api/v1/employees/', {'user': str(admin.pk), 'employee_id': 'ADMIN-1', 'branch': north.pk, 'employment_type': 'PART_TIME'}, format='json')
    assert result.status_code == 201, result.data
    assert result.data['hire_date'] == timezone.localdate().isoformat()
    assert result.data['position'] is None
    admin.refresh_from_db()
    assert admin.branch_id == north.pk
    assert CapabilityService.all_for(admin) == capabilities_before
    overview = client.get('/api/v1/employees/overview/')
    assert overview.data['self_profile_id'] == result.data['id']
    assert overview.data['accounts_without_profile'] == 1


@pytest.mark.django_db
def test_company_wide_leadership_assignment_keeps_recorded_workplace(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    profile = EmployeeProfile.objects.create(company=home, user=admin, employee_id='Leader', branch=north)
    admin.branch = north
    admin.save(update_fields=['branch'])
    position = Position.objects.create(company=home, title='CEO', primary_scope='COMPANY')
    client.force_authenticate(admin)
    result = client.post(f'/api/v1/employees/{profile.pk}/assign-position/', {'position': position.pk}, format='json')
    assert result.status_code == 200, result.data
    profile.refresh_from_db()
    admin.refresh_from_db()
    assert profile.position_id == position.pk
    assert profile.branch_id == admin.branch_id == north.pk


@pytest.mark.django_db
def test_authorized_profile_workplace_edit_keeps_account_context_in_sync(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    result = client.patch(f'/api/v1/employees/{people[0].pk}/', {'branch': south.pk}, format='json')
    assert result.status_code == 200, result.data
    people[0].refresh_from_db()
    people[0].user.refresh_from_db()
    assert people[0].branch_id == people[0].user.branch_id == south.pk


@pytest.mark.django_db
def test_workplace_edit_validates_retained_department_and_team(directory_scope_fixture):
    from organizations.models import Department, Team
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    department = Department.objects.create(company=home, branch=north, name='North department', created_by=admin)
    team = Team.objects.create(company=home, branch=north, department=department, name='North team', created_by=admin)
    people[0].department = department
    people[0].team = team
    people[0].save()
    client.force_authenticate(admin)
    result = client.patch(f'/api/v1/employees/{people[0].pk}/', {'branch': south.pk}, format='json')
    assert result.status_code == 400, result.data
    people[0].refresh_from_db()
    assert people[0].branch_id == north.pk
    result = client.patch(f'/api/v1/employees/{people[0].pk}/', {'branch': south.pk, 'department': None, 'team': None}, format='json')
    assert result.status_code == 200, result.data
    people[0].refresh_from_db()
    assert people[0].branch_id == south.pk and people[0].department is None and people[0].team is None


@pytest.mark.django_db
def test_ordinary_metadata_edit_can_retain_a_position_without_assigning_it(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    position = Position.objects.create(company=home, title='Existing payroll position')
    PositionCapabilityGrant.objects.create(company=home, position=position, capability='VIEW_COMPENSATION')
    people[1].position = position
    people[1].save()
    UserCapabilityGrant.objects.create(company=home, user=people[0].user, capability='MANAGE_EMPLOYEES')
    client.force_authenticate(people[0].user)
    result = client.patch(f'/api/v1/employees/{people[1].pk}/', {'employee_id': 'Updated ID', 'position': position.pk}, format='json')
    assert result.status_code == 200, result.data
    people[1].refresh_from_db()
    assert people[1].position_id == position.pk and people[1].employee_id == 'Updated ID'


@pytest.mark.django_db
def test_duplicate_employee_id_is_a_useful_validation_error(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    result = client.post('/api/v1/employees/', {'user': str(admin.pk), 'employee_id': people[0].employee_id}, format='json')
    assert result.status_code == 400, result.data
    assert not EmployeeProfile.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_legacy_manager_directory_remains_branch_scoped(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(manager)
    result = client.get('/api/v1/employees/overview/')
    assert result.status_code == 200, result.data
    assert result.data['scope'] == 'BRANCHES'
    assert result.data['total_profiles'] == 2
    assert result.data['pending_invitations'] is None


@pytest.mark.django_db
def test_personal_overview_does_not_disclose_company_totals(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(people[0].user)
    result = client.get('/api/v1/employees/overview/')
    assert result.status_code == 200, result.data
    assert result.data['scope'] == 'PERSONAL'
    assert result.data['total_profiles'] == 1
    assert result.data['workspace_accounts'] is None
    assert {item['id'] for item in result.data['branches']} == {north.pk}


@pytest.mark.django_db
def test_employee_action_preview_matches_permissions_and_status(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    active = client.get(f'/api/v1/employees/{people[0].pk}/').data['allowed_actions']
    assert {'PLACE_ON_LEAVE', 'SUSPEND', 'TERMINATE'} <= set(active)
    assert 'RETURN_FROM_LEAVE' not in active and 'VIEW_COMPENSATION' not in active
    on_leave = client.get(f'/api/v1/employees/{people[1].pk}/').data['allowed_actions']
    assert 'RETURN_FROM_LEAVE' in on_leave and 'PLACE_ON_LEAVE' not in on_leave
    terminated = client.get(f'/api/v1/employees/{people[2].pk}/').data['allowed_actions']
    assert not {'REACTIVATE', 'SUSPEND', 'TERMINATE', 'PLACE_ON_LEAVE'} & set(terminated)
    client.force_authenticate(manager)
    assert client.get(f'/api/v1/employees/{people[0].pk}/').data['allowed_actions'] == []


@pytest.mark.django_db
def test_last_admin_profile_cannot_be_suspended(directory_scope_fixture, monkeypatch):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    profile = EmployeeProfile.objects.create(company=home, user=admin, employee_id='Sole administrator')
    UserCapabilityGrant.objects.create(company=home, user=people[0].user, capability='MANAGE_EMPLOYEES')
    client.force_authenticate(people[0].user)
    data = client.get(f'/api/v1/employees/{profile.pk}/').data
    assert 'SUSPEND' not in data['allowed_actions'] and 'TERMINATE' not in data['allowed_actions']
    monkeypatch.setattr('organizations.views.CommunicationService.send', lambda **kwargs: None)
    result = client.post(f'/api/v1/employees/{profile.pk}/suspend/', {'reason': 'Synthetic test'}, format='json')
    assert result.status_code == 400, result.data
    admin.refresh_from_db()
    profile.refresh_from_db()
    assert admin.is_active and profile.status == 'ACTIVE'


@pytest.mark.django_db
def test_leave_action_updates_counts_and_cannot_revive_terminated_profiles(directory_scope_fixture, monkeypatch):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    monkeypatch.setattr('organizations.services.CommunicationService.send', lambda **kwargs: None)
    client.force_authenticate(admin)
    result = client.post(f'/api/v1/employees/{people[0].pk}/leave/', {'reason': 'Synthetic leave'}, format='json')
    assert result.status_code == 200, result.data
    overview = client.get('/api/v1/employees/overview/').data
    assert overview['active'] == 0 and overview['on_leave'] == 2 and overview['current_employees'] == 2
    result = client.post(f'/api/v1/employees/{people[0].pk}/return-from-leave/', {}, format='json')
    assert result.status_code == 200, result.data
    result = client.post(f'/api/v1/employees/{people[2].pk}/leave/', {}, format='json')
    assert result.status_code == 400, result.data
    result = client.post(f'/api/v1/employees/{people[2].pk}/return-from-leave/', {}, format='json')
    assert result.status_code == 400, result.data
    people[2].refresh_from_db()
    assert people[2].status == 'TERMINATED'


@pytest.mark.django_db
def test_profile_metadata_edits_cannot_move_account_or_bypass_employment_actions(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    client.force_authenticate(admin)
    for payload in ({'user': str(manager.pk)}, {'status': 'TERMINATED'}):
        result = client.patch(f'/api/v1/employees/{people[0].pk}/', payload, format='json')
        assert result.status_code == 400, result.data
    people[0].refresh_from_db()
    assert people[0].status == 'ACTIVE' and people[0].user != manager


@pytest.mark.django_db
def test_employee_management_cannot_bootstrap_position_permissions(directory_scope_fixture):
    home, north, south, empty, admin, manager, people, outsider, client = directory_scope_fixture
    position = Position.objects.create(company=home, title='Setup administrator', primary_scope='COMPANY')
    PositionCapabilityGrant.objects.create(company=home, position=position, capability='MANAGE_COMPANY_SETUP')
    UserCapabilityGrant.objects.create(company=home, user=people[0].user, capability='MANAGE_EMPLOYEES')
    client.force_authenticate(people[0].user)
    result = client.patch(f'/api/v1/employees/{people[0].pk}/', {'position': position.pk}, format='json')
    assert result.status_code == 400, result.data
    result = client.post(f'/api/v1/employees/{people[0].pk}/assign-position/', {'position': position.pk}, format='json')
    assert result.status_code == 403, result.data
    people[0].refresh_from_db()
    assert people[0].position is None
