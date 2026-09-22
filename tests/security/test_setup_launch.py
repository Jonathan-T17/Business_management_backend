import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from companies.models import Company
from company_setup.models import CompanySetupState, RolePreset
from forms_engine.models import FormTemplate, FormSubmission


@pytest.fixture
def workspace(django_user_model):
    company = Company.objects.create(name='Guided setup')
    user = django_user_model.objects.create_user(
        email='setup-launch@example.test', company=company, role='ADMIN',
        is_active=True, account_state='ACTIVE', email_verified=True,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')
    return company, user, client


@pytest.mark.django_db
def test_real_token_setup_gate_and_configuration_completion(workspace):
    company, user, client = workspace
    base = '/api/v1/company-setup/'
    assert client.get(base+'access/').data['setup_required'] is True
    blocked = client.get('/api/v1/tasks/')
    assert blocked.status_code == 403
    assert blocked.data['error']['code'] == 'COMPANY_SETUP_REQUIRED'
    assert client.post('/api/v1/form-submissions/', {}, format='json').status_code == 403
    assert client.get('/api/v1/company/').status_code == 200
    assert client.post(base+'steps/complete/', {'step':'company'}).status_code == 400
    # Legacy checklist marks cannot fabricate readiness.
    CompanySetupState.objects.create(company=company, completed_steps=['company','permissions','forms'])
    status = client.get(base+'status/').data
    assert next(s for s in status['steps'] if s['code']=='company')['status'] != 'COMPLETED'
    assert client.post(base+'finish/').status_code == 400
    response = client.patch(f'/api/v1/company/{company.pk}/', {
        'official_name':'Guided organisation', 'country':'rw',
        'timezone':'Africa/Kigali', 'default_currency':'rwf',
    }, format='json')
    assert response.status_code == 200, response.data
    assert response.data['country'] == 'RW'
    assert response.data['default_currency'] == 'RWF'
    for field,value in [('timezone','Invalid/Place'),('country','Rwanda'),('default_currency','12')]:
        assert client.patch(f'/api/v1/company/{company.pk}/', {field:value}, format='json').status_code == 400
    role = client.post(base+'role-presets/', {'code':'operator','name':'Operator','capabilities':['USE_FORMS']}, format='json')
    assert role.status_code == 201, role.data
    form = FormTemplate.objects.create(company=company,name='Daily operations',code='daily')
    assert client.post(base+'finish/').status_code == 400  # drafts do not count
    form.lifecycle_status='PUBLISHED'
    form.save(update_fields=['lifecycle_status'])
    from companies.models import Branch
    from organizations.models import Position
    Branch.objects.create(company=company,name="Headquarters")
    Position.objects.create(company=company,title="CEO")
    for step in ("organization", "departments", "positions", "permissions", "employees"):
        review=client.post(base+'steps/complete/', {"step":step})
        assert review.status_code == 200, review.data
        if step == "organization":
            separate = client.get(base+'status/').data
            assert next(s for s in separate['steps'] if s['code']=='departments')['status'] != 'COMPLETED'
            assert client.post(base+'finish/').status_code == 400
    status=client.get(base+'status/').data
    assert status['progress'] == 88
    assert status['current_step'] == 'finish'
    assert client.post(base+'finish/').status_code == 200
    company.refresh_from_db()
    assert company.setup_completed_at is not None
    assert client.get(base+'status/').data['progress'] == 100
    assert client.get(base+'access/').data['setup_required'] is False
    assert client.get('/api/v1/dashboard/').status_code == 200


@pytest.mark.django_db
def test_other_company_configuration_does_not_complete_setup(workspace):
    company, user, client = workspace
    other = Company.objects.create(name='Unrelated ready company')
    RolePreset.objects.create(company=other,code='operator',name='Operator')
    FormTemplate.objects.create(company=other,name='Other form',code='other',lifecycle_status='PUBLISHED')
    status=client.get('/api/v1/company-setup/status/').data
    assert not status['readiness']['ready']
    assert 'PUBLISHED_FORM' in {issue['code'] for issue in status['readiness']['issues']}
    user.role='EMPLOYEE'
    user.save(update_fields=['role'])
    assert client.get('/api/v1/company-setup/access/').data['setup_required']
    assert client.get('/api/v1/company-setup/status/').status_code == 403
    assert client.get('/api/v1/reports/').status_code == 403


@pytest.mark.django_db
def test_submission_charts_are_scoped_and_filtered(workspace):
    from subscriptions.models import Plan, Subscription
    company, user, client = workspace
    CompanySetupState.objects.create(company=company,onboarding_completed=True,setup_version=2)
    from core.capabilities import Capabilities
    from core.capability_service import CapabilityService
    # Company admins receive operational analytics without an additional grant.
    assert CapabilityService.has(user, Capabilities.VIEW_COMPANY_ANALYTICS)
    for restricted in (Capabilities.VIEW_COMPENSATION, Capabilities.VIEW_HR_CONFIDENTIAL,
                       Capabilities.VIEW_FINANCIAL_DATA, Capabilities.VIEW_MANAGEMENT_CONFIDENTIAL):
        assert not CapabilityService.has(user, restricted)
    plan=Plan.objects.create(name='Charts',max_users=10,max_projects=10,price_monthly=0)
    Subscription.objects.create(company=company,plan=plan)
    other=Company.objects.create(name='Private chart company')
    for owner,code in [(company,'visible'),(other,'foreign')]:
        form=FormTemplate.objects.create(company=owner,name=code,code=code)
        FormSubmission.objects.create(company=owner,template=form,submitted_by=user,
                                      reference_number=code,status='APPROVED')
    response=client.get('/api/v1/analytics/overview/')
    assert response.status_code == 200, response.data
    assert response.data['submissions']['approved'] == 1
    assert sum(p['value'] for p in response.data['submission_trend']) == 1
    empty=client.get('/api/v1/analytics/overview/',{'end_date':'2000-01-01'})
    assert empty.data['submissions']['approved'] == 0
    assert empty.data['submission_trend'] == []


@pytest.mark.django_db
def test_existing_company_must_review_expanded_setup(workspace):
    company, user, client = workspace
    CompanySetupState.objects.create(company=company,onboarding_completed=True,completed_steps=["company","permissions","forms","finish"])
    assert client.get('/api/v1/company-setup/access/').data['setup_required']
    assert not client.get('/api/v1/company-setup/status/').data['onboarding_completed']
    assert client.get('/api/v1/dashboard/').status_code == 403


@pytest.mark.django_db
def test_position_relationships_and_access(workspace):
    from companies.models import Branch
    from organizations.models import Department, Position
    company, user, client = workspace
    other = Company.objects.create(name="Other")
    foreign = Branch.objects.create(company=other,name="Foreign")
    branch = Branch.objects.create(company=company,name="Headquarters")
    department = Department.objects.create(company=company,branch=branch,name="Finance",created_by=user)
    root = '/api/v1/organizations/positions/'
    assert client.post(root,{"title":"Invalid", "branch":foreign.pk}).status_code == 400
    assert client.post(root,{"title":"Invalid department", "department":department.pk}).status_code == 400
    created = client.post(root,{"title":"Finance Manager", "branch":branch.pk,"department":department.pk},format="json")
    assert created.status_code == 201, created.data
    first = created.data['id']
    second = client.post(root,{"title":"CEO"},format="json").data['id']
    response=client.patch(f'{root}{first}/',{'reports_to':second},format='json')
    assert response.status_code == 200, response.data
    assert client.patch(f'{root}{second}/',{'reports_to':first}).status_code == 400
    access = f'/api/v1/company-setup/positions/{first}/access/'
    assert client.put(access,{'capabilities':['VIEW_COMPANY_ANALYTICS']},format='json').status_code == 200
    assert client.get(access).data['capabilities'] == ['VIEW_COMPANY_ANALYTICS']
    assert client.put(access,{'capabilities':['VIEW_COMPENSATION']},format='json').status_code == 403
    assert client.get(access).data['capabilities'] == ['VIEW_COMPANY_ANALYTICS']
    assert client.put(access,{'capabilities':[]},format='json').status_code == 200


@pytest.mark.django_db
def test_invitation_assigns_prepared_position(workspace):
    from datetime import timedelta
    from django.utils import timezone
    from companies.models import Branch, CompanyInvite
    from companies.services import CompanyInviteService
    from organizations.models import Position, EmployeeProfile, PositionCapabilityGrant
    from subscriptions.models import Plan, Subscription
    from core.capability_service import CapabilityService
    company, admin, client = workspace
    plan=Plan.objects.create(name="Invite plan",max_users=10,max_projects=10,price_monthly=0)
    Subscription.objects.create(company=company,plan=plan)
    branch=Branch.objects.create(company=company,name="Headquarters")
    position=Position.objects.create(company=company,title="Operations",branch=branch)
    PositionCapabilityGrant.objects.create(company=company,position=position,capability="SUBMIT_FORMS")
    user=type(admin).objects.create_user(email="joining@example.test",role="EMPLOYEE")
    invite=CompanyInvite.objects.create(company=company,email=user.email,role="EMPLOYEE",position=position,created_by=admin,expires_at=timezone.now()+timedelta(days=1))
    CompanyInviteService.accept_invite(invite=invite,user=user)
    profile=EmployeeProfile.objects.get(user=user)
    assert profile.position_id == position.pk and profile.branch_id == branch.pk
    user.refresh_from_db()
    assert CapabilityService.has(user,"SUBMIT_FORMS")


@pytest.mark.django_db
def test_unassigned_invitee_is_restricted_until_position_assignment(workspace):
    from datetime import timedelta
    from django.utils import timezone
    from companies.models import CompanyInvite
    from companies.services import CompanyInviteService
    from organizations.models import Position, EmployeeProfile, PositionCapabilityGrant, UserCapabilityGrant
    from subscriptions.models import Plan, Subscription
    from core.capability_service import CapabilityService
    company, admin, _ = workspace
    plan = Plan.objects.create(name="Pending invite plan", max_users=10, max_projects=10, price_monthly=0)
    Subscription.objects.create(company=company, plan=plan)
    user = type(admin).objects.create_user(email="pending-position@example.test", role="EMPLOYEE",
        is_active=True, account_state="ACTIVE", email_verified=True)
    invite = CompanyInvite.objects.create(company=company, email=user.email, role="EMPLOYEE",
        created_by=admin, expires_at=timezone.now()+timedelta(days=1))
    CompanyInviteService.accept_invite(invite=invite, user=user)
    profile = EmployeeProfile.objects.get(user=user)
    assert profile.position_id is None
    CompanySetupState.objects.create(company=company, onboarding_completed=True, setup_version=2)
    UserCapabilityGrant.objects.create(company=company, user=user, capability="VIEW_ALL_REPORTS")
    assert not CapabilityService.all_for(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(user)}')
    assert client.get('/api/v1/company-setup/access/').data['awaiting_position'] is True
    assert client.get('/api/v1/profile/').status_code == 200
    for path in ('branches/', 'form-templates/', 'reports/', 'users/', 'company-setup/status/'):
        response = client.get('/api/v1/'+path)
        assert response.status_code == 403, (path, response.data)
    position = Position.objects.create(company=company, title="Assigned operator")
    PositionCapabilityGrant.objects.create(company=company, position=position, capability="USE_FORMS")
    profile.position = position
    profile.save(update_fields=['position'])
    assert client.get('/api/v1/company-setup/access/').data['awaiting_position'] is False
    user.refresh_from_db()
    assert CapabilityService.has(user, 'USE_FORMS')
