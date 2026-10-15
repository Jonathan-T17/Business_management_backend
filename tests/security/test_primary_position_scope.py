from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from companies.models import Branch, Company
from core.capability_service import CapabilityService as CS
from core.position_scope import PositionScope
from core.visibility import VisibilityService
from forms_engine.access import FormAccess
from forms_engine.models import FormSubmission, FormTemplate
from forms_engine.services import FormSubmissionService
from organizations.models import EmployeeProfile, Position, PositionCapabilityGrant, UserCapabilityGrant
from reports.models import Report


@pytest.fixture
def primary_workspace(django_user_model):
    company = Company.objects.create(name="Primary position scope")
    branch = Branch.objects.create(company=company, name="Northern office")
    other = Branch.objects.create(company=company, name="Southern office")
    admin = django_user_model.objects.create_user(email="primary-admin@example.test", company=company, role="ADMIN", is_active=True)
    employee = django_user_model.objects.create_user(email="primary-employee@example.test", company=company, branch=branch, role="EMPLOYEE", is_active=True)
    position = Position.objects.create(company=company, branch=branch, title="Branch operations", primary_scope="BRANCH")
    EmployeeProfile.objects.create(user=employee, company=company, employee_id="BR-1", branch=branch, position=position)
    caps = ["USE_FORMS", "SUBMIT_FORMS", "VIEW_ALL_REPORTS", "VIEW_FORM_SUBMISSIONS", "REVIEW_SUBMISSIONS", "VIEW_COMPANY_ANALYTICS"]
    for capability in caps:
        PositionCapabilityGrant.objects.create(company=company, position=position, capability=capability)
    client = APIClient()
    client.force_authenticate(admin)
    return company, branch, other, admin, employee, position, caps, client


@pytest.mark.django_db
def test_primary_position_limits_private_reports_submissions_forms_and_analytics(primary_workspace):
    from subscriptions.models import Plan, Subscription
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    for capability in caps:
        assert CS.has(employee, capability)
        assert not CS.has_company(employee, capability)
    templates = []
    for location in (branch, other):
        Report.objects.create(company=company, branch=location, title=location.name, description="Private", created_by=admin, visibility="PRIVATE")
        template = FormTemplate.objects.create(company=company, branch=location, name=location.name, code=str(location.pk), lifecycle_status="PUBLISHED")
        templates.append(template)
        FormSubmission.objects.create(company=company, branch=location, template=template, submitted_by=admin, reference_number=str(location.pk))
    assert list(VisibilityService.reports_queryset(user=employee, queryset=Report.objects.all()).values_list("branch_id", flat=True)) == [branch.pk]
    assert not VisibilityService.can_view_report(employee, Report.objects.get(branch=other))
    assert list(VisibilityService.form_submissions_queryset(user=employee, queryset=FormSubmission.objects.all()).values_list("branch_id", flat=True)) == [branch.pk]
    assert FormAccess.eligible(employee, templates[0])
    assert not FormAccess.eligible(employee, templates[1])
    general = FormTemplate.objects.create(company=company, name="Company daily form", code="general", lifecycle_status="PUBLISHED")
    assert FormAccess.eligible(employee, general)
    submission = FormSubmissionService.create_submission(template=general, user=employee)
    assert submission.branch_id == branch.pk
    plan = Plan.objects.create(name="Primary scope", max_users=10, max_projects=10, price_monthly=0)
    Subscription.objects.create(company=company, plan=plan)
    client.force_authenticate(employee)
    result = client.get("/api/v1/analytics/overview/")
    assert result.status_code == 200, result.data
    assert sum(result.data["submissions"].values()) == 2

    # Changing a primary position need not move someone's organisational home.
    # A general form is filed under the location contributing submission access.
    employee.branch = other
    employee.save(update_fields=["branch"])
    employee.employee_profile.branch = other
    employee.employee_profile.save(update_fields=["branch"])
    second = FormSubmissionService.create_submission(template=general, user=employee)
    assert second.branch_id == branch.pk
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        FormSubmissionService.create_submission(template=general, user=employee, branch=other)


@pytest.mark.django_db
def test_primary_scope_is_explicit_and_invalid_changes_are_atomic(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    endpoint = f"/api/v1/company-setup/positions/{position.pk}/access/"
    assert client.get(endpoint).data["scope_label"] == branch.name
    response = client.put(endpoint, {"primary_scope": "BRANCH", "capabilities": caps + ["MANAGE_ORGANIZATION"]}, format="json")
    assert response.status_code == 400, response.data
    assert set(client.get(endpoint).data["capabilities"]) == set(caps)
    result = client.put(endpoint, {"primary_scope": "COMPANY", "capabilities": caps}, format="json")
    assert result.status_code == 200, result.data
    employee.refresh_from_db()
    assert CS.has_company(employee, "VIEW_ALL_REPORTS")
    assert client.put(endpoint, {"capabilities": caps}, format="json").data["primary_scope"] == "COMPANY"
    no_location = Position.objects.create(company=company, title="Unplaced")
    assert client.put(f"/api/v1/company-setup/positions/{no_location.pk}/access/", {"primary_scope": "BRANCH", "capabilities": []}, format="json").status_code == 400
    client.force_authenticate(employee)
    assert client.put(endpoint, {"primary_scope": "COMPANY", "capabilities": []}, format="json").status_code == 403


@pytest.mark.django_db
def test_primary_scope_cannot_expand_confidential_access_or_survive_inactive_location(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    # Even malformed database grants cannot escape the supported scoped set.
    PositionCapabilityGrant.objects.create(company=company, position=position, capability="VIEW_COMPENSATION")
    assert not CS.has(employee, "VIEW_COMPENSATION")
    from organizations.services import CapabilityGrantService
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        CapabilityGrantService.grant_position(company=company, position=position, capability="MANAGE_ORGANIZATION", actor=admin)
    branch.is_active = False
    branch.save(update_fields=["is_active"])
    employee.refresh_from_db()
    assert not CS.has(employee, "VIEW_ALL_REPORTS")
    assert not PositionScope.branches_for(employee, "VIEW_ALL_REPORTS")
    assert not PositionScope.position_users(company=company, position=position, branch_id=branch.pk).exists()


@pytest.mark.django_db
def test_primary_scope_limits_position_routing_and_preserves_other_explicit_authority(primary_workspace):
    from workflows.services import WorkflowService
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    step = SimpleNamespace(recipient_type="POSITION", recipient_position=position)
    assert WorkflowService.resolve_recipients(step=step, company=company, submitted_by=admin, target=SimpleNamespace(branch_id=branch.pk)) == [employee]
    assert WorkflowService.resolve_recipients(step=step, company=company, submitted_by=admin, target=SimpleNamespace(branch_id=other.pk)) == []
    assert not PositionScope.position_users(company=company, position=position).exists()
    UserCapabilityGrant.objects.create(company=company, user=employee, capability="VIEW_ALL_REPORTS")
    assert CS.has_company(employee, "VIEW_ALL_REPORTS")


@pytest.mark.django_db
def test_new_branch_positions_start_scoped_and_structural_edits_cannot_bypass_it(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    response = client.post("/api/v1/organizations/positions/", {"title": "Branch analyst", "branch": branch.pk, "primary_scope": "COMPANY"}, format="json")
    assert response.status_code == 201, response.data
    assert response.data["primary_scope"] == "BRANCH"
    endpoint = f"/api/v1/organizations/positions/{response.data['id']}/"
    assert client.patch(endpoint, {"primary_scope": "COMPANY"}, format="json").data["primary_scope"] == "BRANCH"
    assert client.patch(endpoint, {"branch": None}, format="json").status_code == 400

    # Structure-edit authority alone must not move an access boundary.
    UserCapabilityGrant.objects.create(company=company, user=employee, capability="MANAGE_ORGANIZATION")
    client.force_authenticate(employee)
    position_endpoint = f"/api/v1/organizations/positions/{position.pk}/"
    refused = client.patch(position_endpoint, {"branch": other.pk}, format="json")
    assert refused.status_code == 400, refused.data
    position.refresh_from_db()
    assert position.branch_id == branch.pk
    assert client.patch(position_endpoint, {"description": "Updated responsibilities"}, format="json").status_code == 200
    client.force_authenticate(admin)
    moved = client.patch(position_endpoint, {"branch": other.pk}, format="json")
    assert moved.status_code == 200, moved.data
    employee.refresh_from_db()
    assert PositionScope.branches_for(employee, "VIEW_ALL_REPORTS") == {other.pk}

@pytest.mark.django_db
def test_general_form_branch_choices_and_saved_context_are_permission_bound(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    general = FormTemplate.objects.create(company=company, name='Multi-location form', code='multi-location', lifecycle_status='PUBLISHED')
    extra = Position.objects.create(company=company, title='Additional form work')
    PositionCapabilityGrant.objects.create(company=company, position=extra, capability='USE_FORMS')
    assignment = EmployeePositionAssignment.objects.create(company=company, employee=employee.employee_profile, position=extra, scope='BRANCHES')
    assignment.branches.add(other)
    foreign_company = Company.objects.create(name='Foreign filing company')
    foreign = Branch.objects.create(company=foreign_company, name='Foreign filing branch')
    inactive = Branch.objects.create(company=company, name='Inactive filing branch', is_active=False)
    client.force_authenticate(employee)
    url = f'/api/v1/form-templates/{general.pk}/initial-values/'
    response = client.get(url)
    assert response.status_code == 200, response.data
    assert {item['id'] for item in response.data['branch_choices']} == {branch.pk, other.pk}
    assert client.get(url, {'branch': other.pk}).data['entry_branch']['id'] == other.pk
    for denied in (foreign, inactive):
        assert client.get(url, {'branch': denied.pk}).status_code == 400
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            FormSubmissionService.create_submission(template=general, user=employee, branch=denied)
    entry = FormSubmissionService.create_submission(template=general, user=employee, branch=other)
    assert entry.branch_id == other.pk
    response = client.patch(f'/api/v1/form-submissions/{entry.pk}/', {'branch': branch.pk}, format='json')
    assert response.status_code == 400, response.data
    entry.refresh_from_db()
    assert entry.branch_id == other.pk
    targeted = FormTemplate.objects.create(company=company, name='Targeted filing form', code='targeted-filing', lifecycle_status='PUBLISHED', audience_branch_ids=[branch.pk])
    assert {item['id'] for item in client.get(f'/api/v1/form-templates/{targeted.pk}/initial-values/').data['branch_choices']} == {branch.pk}
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        FormSubmissionService.create_submission(template=targeted, user=employee, branch=other)


@pytest.mark.django_db
def test_fixed_branch_form_does_not_offer_other_company_branches(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    template = FormTemplate.objects.create(company=company, branch=branch, name='Fixed filing form', code='fixed-filing', lifecycle_status='PUBLISHED')
    client.force_authenticate(employee)
    response = client.get(f'/api/v1/form-templates/{template.pk}/initial-values/')
    assert response.status_code == 200, response.data
    assert response.data['branch_choices'] == [{'id': branch.pk, 'name': branch.name}]
    from django.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        FormSubmissionService.create_submission(template=template, user=admin, branch=other)

@pytest.mark.django_db
def test_combined_access_summary_matches_authorization_and_scopes(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    UserCapabilityGrant.objects.create(company=company, user=employee, capability='VIEW_PERSONAL_DATA')
    extra = Position.objects.create(company=company, title='Additional branch reader')
    PositionCapabilityGrant.objects.create(company=company, position=extra, capability='VIEW_ALL_REPORTS')
    assignment = EmployeePositionAssignment.objects.create(company=company, employee=employee.employee_profile, position=extra, scope='BRANCHES')
    assignment.branches.add(other)
    endpoint = f'/api/v1/employees/{employee.employee_profile.pk}/access-summary/'
    response = client.get(endpoint)
    assert response.status_code == 200, response.data
    actions = {item['code']: item for item in response.data['actions']}
    assert set(actions) == CS.all_for(employee)
    assert all(item['company_wide'] == CS.has_company(employee, code) for code, item in actions.items())
    assert {item['id'] for item in actions['VIEW_ALL_REPORTS']['branches']} == {branch.pk, other.pk}
    assert set(actions['VIEW_ALL_REPORTS']['sources']) == {'Primary position: Branch operations', 'Additional position: Additional branch reader'}
    assert actions['VIEW_PERSONAL_DATA']['sensitive']
    assert actions['VIEW_PERSONAL_DATA']['company_wide']
    assert actions['VIEW_PERSONAL_DATA']['sources'] == ['Direct permission']
    client.force_authenticate(employee)
    assert client.get(endpoint).status_code == 403
    stranger_company = Company.objects.create(name='Foreign access summary')
    foreign_admin = type(employee).objects.create_user(email='foreign-summary@example.test', company=stranger_company, role='ADMIN', is_active=True)
    client.force_authenticate(foreign_admin)
    assert client.get(endpoint).status_code == 404
    employee.is_active = False
    employee.save(update_fields=['is_active'])
    client.force_authenticate(admin)
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.data['actions'] == [] and not response.data['account_active']

@pytest.mark.django_db
def test_assignment_preview_matches_saved_access_without_writing(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    from organizations.access_summary import employee_access_summary
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    extra = Position.objects.create(company=company, title='Preview branch reader')
    PositionCapabilityGrant.objects.create(company=company, position=extra, capability='VIEW_ALL_REPORTS')
    payload = {'employee': employee.employee_profile.pk, 'position': extra.pk, 'scope': 'BRANCHES', 'branches': [other.pk], 'is_active': True}
    before = employee_access_summary(employee.employee_profile)
    count = EmployeePositionAssignment.objects.count()
    response = client.post('/api/v1/organizations/position-assignments/preview/', payload, format='json')
    assert response.status_code == 200, response.data
    projected = response.data
    assert EmployeePositionAssignment.objects.count() == count
    assert employee_access_summary(employee.employee_profile) == before
    assert {b['id'] for item in projected['actions'] if item['code'] == 'VIEW_ALL_REPORTS' for b in item['branches']} == {branch.pk, other.pk}
    result = client.post('/api/v1/organizations/position-assignments/', payload, format='json')
    assert result.status_code == 201, result.data
    assert employee_access_summary(employee.employee_profile) == projected
    assignment = EmployeePositionAssignment.objects.get(pk=result.data['id'])
    result = client.post('/api/v1/organizations/position-assignments/preview/', {'assignment_id': assignment.pk, 'is_active': False}, format='json')
    assert result.status_code == 200, result.data
    reports = next(item for item in result.data['actions'] if item['code'] == 'VIEW_ALL_REPORTS')
    assert {b['id'] for b in reports['branches']} == {branch.pk}
    assert reports['sources'] == ['Primary position: Branch operations']
    assignment.refresh_from_db()
    assert assignment.is_active
    actual = client.patch(f'/api/v1/organizations/position-assignments/{assignment.pk}/', {'is_active': False}, format='json')
    assert actual.status_code == 200, actual.data
    assert employee_access_summary(employee.employee_profile) == result.data


@pytest.mark.django_db
def test_assignment_preview_preserves_direct_access_and_enforces_scope(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    extra = Position.objects.create(company=company, title='Preview company reader')
    PositionCapabilityGrant.objects.create(company=company, position=extra, capability='VIEW_ALL_REPORTS')
    assignment = EmployeePositionAssignment.objects.create(company=company, employee=employee.employee_profile, position=extra, scope='COMPANY')
    UserCapabilityGrant.objects.create(company=company, user=employee, capability='VIEW_ALL_REPORTS')
    endpoint = '/api/v1/organizations/position-assignments/preview/'
    response = client.post(endpoint, {'assignment_id': assignment.pk, 'is_active': False}, format='json')
    assert response.status_code == 200, response.data
    action = next(item for item in response.data['actions'] if item['code'] == 'VIEW_ALL_REPORTS')
    assert action['company_wide'] and 'Direct permission' in action['sources']
    foreign_company = Company.objects.create(name='Foreign preview scope')
    foreign = Branch.objects.create(company=foreign_company, name='Foreign preview branch')
    response = client.post(endpoint, {'assignment_id': assignment.pk, 'scope': 'BRANCHES', 'branches': [foreign.pk]}, format='json')
    assert response.status_code == 400, response.data
    client.force_authenticate(employee)
    assert client.post(endpoint, {'assignment_id': assignment.pk, 'is_active': False}, format='json').status_code == 403
    foreign_admin = type(employee).objects.create_user(email='foreign-preview@example.test', company=foreign_company, role='ADMIN', is_active=True)
    client.force_authenticate(foreign_admin)
    assert client.post(endpoint, {'assignment_id': assignment.pk, 'is_active': False}, format='json').status_code == 404


@pytest.mark.django_db
def test_assignment_preview_does_not_bootstrap_confidential_access(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    confidential = Position.objects.create(company=company, title='Preview confidential role')
    PositionCapabilityGrant.objects.create(company=company, position=confidential, capability='VIEW_COMPENSATION')
    payload = {'employee': employee.employee_profile.pk, 'position': confidential.pk, 'scope': 'COMPANY', 'branches': []}
    response = client.post('/api/v1/organizations/position-assignments/preview/', payload, format='json')
    assert response.status_code == 403, response.data

@pytest.mark.django_db
def test_assignment_preview_rejects_duplicate_and_employee_rebinding(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    extra = Position.objects.create(company=company, title='Existing reviewed position')
    PositionCapabilityGrant.objects.create(company=company, position=extra, capability='VIEW_ALL_REPORTS')
    assignment = EmployeePositionAssignment.objects.create(company=company, employee=employee.employee_profile, position=extra, scope='COMPANY')
    endpoint = '/api/v1/organizations/position-assignments/preview/'
    payload = {'employee': employee.employee_profile.pk, 'position': extra.pk, 'scope': 'COMPANY', 'branches': []}
    assert client.post(endpoint, payload, format='json').status_code == 400
    replacement = EmployeeProfile.objects.create(company=company, user=admin, employee_id='Preview-other-person', branch=branch)
    response = client.post(endpoint, {'assignment_id': assignment.pk, 'employee': replacement.pk}, format='json')
    assert response.status_code == 400, response.data
    response = client.patch(f'/api/v1/organizations/position-assignments/{assignment.pk}/', {'employee': replacement.pk}, format='json')
    assert response.status_code == 400, response.data
    assignment.refresh_from_db()
    assert assignment.employee_id == employee.employee_profile.pk

@pytest.mark.django_db
def test_primary_position_preview_matches_save_and_keeps_other_sources(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    from organizations.access_summary import employee_access_summary
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    new_position = Position.objects.create(company=company, branch=other, title='New primary branch position', primary_scope='BRANCH')
    PositionCapabilityGrant.objects.create(company=company, position=new_position, capability='VIEW_ALL_REPORTS')
    retained = EmployeePositionAssignment.objects.create(company=company, employee=employee.employee_profile, position=position, scope='BRANCHES')
    retained.branches.add(branch)
    UserCapabilityGrant.objects.create(company=company, user=employee, capability='VIEW_PERSONAL_DATA')
    profile = employee.employee_profile
    old = employee_access_summary(profile)
    response = client.post(f'/api/v1/employees/{profile.pk}/preview-position/', {'position': new_position.pk}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['before'] == old
    assert profile.position_id == position.pk and employee.branch_id == branch.pk
    profile.refresh_from_db()
    assert profile.position_id == position.pk
    result = client.post(f'/api/v1/employees/{profile.pk}/assign-position/', {'position': new_position.pk}, format='json')
    assert result.status_code == 200, result.data
    profile.refresh_from_db()
    employee.refresh_from_db()
    profile.user = employee
    employee.employee_profile = profile
    assert employee_access_summary(profile) == response.data['after']
    assert profile.branch_id == branch.pk


@pytest.mark.django_db
def test_primary_preview_unlocks_invitation_only_after_active_assignment(primary_workspace):
    from organizations.access_summary import employee_access_summary
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    invited = type(employee).objects.create_user(email='primary-preview-invited@example.test', company=company, branch=other, role='EMPLOYEE', position_required=True, is_active=True)
    profile = EmployeeProfile.objects.create(company=company, user=invited, employee_id='Preview-invited', branch=other)
    response = client.post(f'/api/v1/employees/{profile.pk}/preview-position/', {'position': position.pk}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['before']['actions'] == []
    assert response.data['after']['actions']
    profile.refresh_from_db()
    invited.refresh_from_db()
    assert not profile.position_id and invited.position_required and invited.branch_id == other.pk
    result = client.post(f'/api/v1/employees/{profile.pk}/assign-position/', {'position': position.pk}, format='json')
    assert result.status_code == 200, result.data
    invited.refresh_from_db()
    profile.refresh_from_db()
    profile.user = invited
    invited.employee_profile = profile
    assert employee_access_summary(profile) == response.data['after']
    assert invited.branch_id == branch.pk


@pytest.mark.django_db
def test_position_wide_preview_matches_primary_and_additional_holder_access(primary_workspace):
    from organizations.models import EmployeePositionAssignment
    from organizations.access_summary import employee_access_summary
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    secondary_user = type(employee).objects.create_user(email='position-preview-secondary@example.test', full_name='Secondary holder', company=company, branch=other, role='EMPLOYEE', is_active=True)
    secondary = EmployeeProfile.objects.create(company=company, user=secondary_user, employee_id='Preview-secondary', branch=other)
    extra = EmployeePositionAssignment.objects.create(company=company, employee=secondary, position=position, scope='BRANCHES')
    extra.branches.add(other)
    UserCapabilityGrant.objects.create(company=company, user=employee, capability='SUBMIT_FORMS')
    endpoint = f'/api/v1/company-setup/positions/{position.pk}/access/preview/'
    payload = {'capabilities':['VIEW_ALL_REPORTS'], 'primary_scope':'COMPANY'}
    response = client.post(endpoint, payload, format='json')
    assert response.status_code == 200, response.data
    assert response.data['count'] == 2
    projected = {item['before']['employee']:item['after'] for item in response.data['results']}
    position.refresh_from_db()
    assert position.primary_scope == 'BRANCH'
    assert set(position.capability_grants.filter(is_active=True).values_list('capability',flat=True)) == set(caps)
    result = client.put(f'/api/v1/company-setup/positions/{position.pk}/access/', payload, format='json')
    assert result.status_code == 200, result.data
    for profile in (employee.employee_profile, secondary):
        profile.refresh_from_db()
        profile.user.refresh_from_db()
        profile.user.employee_profile = profile
        assert employee_access_summary(profile) == projected[profile.pk]
    reports = next(item for item in projected[secondary.pk]['actions'] if item['code']=='VIEW_ALL_REPORTS')
    assert not reports['company_wide'] and reports['branches'] == [{'id':other.pk,'name':other.name}]


@pytest.mark.django_db
def test_position_wide_preview_pages_and_security_boundaries(primary_workspace):
    company, branch, other, admin, employee, position, caps, client = primary_workspace
    for index in range(25):
        user = type(employee).objects.create_user(email=f'impact-page-{index}@example.test', full_name=f'Impact person {index:02}', company=company, branch=branch, role='EMPLOYEE', is_active=True)
        EmployeeProfile.objects.create(company=company, user=user, employee_id=f'Impact-{index}', branch=branch, position=position)
    endpoint = f'/api/v1/company-setup/positions/{position.pk}/access/preview/'
    payload = {'capabilities':['VIEW_ALL_REPORTS'], 'primary_scope':'BRANCH'}
    first = client.post(endpoint, payload, format='json')
    second = client.post(endpoint+'?page=2', payload, format='json')
    assert first.status_code == second.status_code == 200
    assert first.data['count'] == 26 and len(first.data['results']) == 25 and len(second.data['results']) == 1
    assert {item['before']['employee'] for item in first.data['results']}.isdisjoint({item['before']['employee'] for item in second.data['results']})
    assert client.post(endpoint, {'capabilities':['VIEW_COMPENSATION'], 'primary_scope':'COMPANY'}, format='json').status_code == 403
    client.force_authenticate(employee)
    assert client.post(endpoint, payload, format='json').status_code == 403
    foreign_company = Company.objects.create(name='Foreign position impact')
    foreign_admin = type(employee).objects.create_user(email='foreign-impact@example.test', company=foreign_company, role='ADMIN', is_active=True)
    client.force_authenticate(foreign_admin)
    assert client.post(endpoint, payload, format='json').status_code == 404
