import pytest
from rest_framework.test import APIClient
from companies.models import Company, Branch
from organizations.models import EmployeeProfile, Position, PositionCapabilityGrant, EmployeePositionAssignment
from core.capability_service import CapabilityService as CS
from core.visibility import VisibilityService
from core.position_scope import PositionScope
from reports.models import Report
from forms_engine.models import FormTemplate, FormSubmission

@pytest.fixture
def setup(django_user_model):
    company=Company.objects.create(name="Assignments")
    other=Company.objects.create(name="Foreign")
    admin=django_user_model.objects.create_user(email="admin-assignment@test.example",company=company,role="ADMIN")
    user=django_user_model.objects.create_user(email="employee-assignment@test.example",company=company,role="EMPLOYEE",is_active=True)
    employee=EmployeeProfile.objects.create(company=company,user=user,employee_id="E-1")
    a=Branch.objects.create(company=company,name="A")
    b=Branch.objects.create(company=company,name="B")
    foreign=Branch.objects.create(company=other,name="Foreign")
    position=Position.objects.create(company=company,title="Regional reporting")
    for cap in ("VIEW_ALL_REPORTS","VIEW_FORM_SUBMISSIONS","SUBMIT_FORMS","VIEW_COMPANY_ANALYTICS"):
        PositionCapabilityGrant.objects.create(company=company,position=position,capability=cap)
    client=APIClient();client.force_authenticate(admin)
    return company,other,admin,user,employee,a,b,foreign,position,client

@pytest.mark.django_db
def test_scoped_assignment_visibility_and_revocation(setup):
    company,other,admin,user,employee,a,b,foreign,position,client=setup
    root='/api/v1/organizations/position-assignments/'
    payload={"employee":employee.pk,"position":position.pk,"scope":"BRANCHES","branches":[a.pk]}
    invalid=client.post(root,{**payload,"branches":[foreign.pk]},format="json")
    assert invalid.status_code==400,invalid.data
    response=client.post(root,payload,format="json")
    assert response.status_code==201,response.data
    assignment_id=response.data['id']
    assert CS.has(user,"VIEW_ALL_REPORTS")
    assert not CS.has_company(user,"VIEW_ALL_REPORTS")
    assert not CS.has(user,"MANAGE_ORGANIZATION")
    for branch in (a,b,foreign):
        Report.objects.create(company=branch.company,branch=branch,title=branch.name,description="test",created_by=admin,visibility="PRIVATE")
        form=FormTemplate.objects.create(company=branch.company,branch=branch,name=branch.name,code=branch.name)
        FormSubmission.objects.create(company=branch.company,branch=branch,template=form,submitted_by=admin,reference_number=branch.name)
    visible=VisibilityService.reports_queryset(user=user,queryset=Report.objects.all())
    assert list(visible.values_list('branch_id',flat=True))==[a.pk]
    assert list(VisibilityService.form_submissions_queryset(user=user,queryset=FormSubmission.objects.all()).values_list('branch_id',flat=True))==[a.pk]
    assert not VisibilityService.can_view_report(user,Report.objects.get(branch=b))
    assert client.patch(f'{root}{assignment_id}/',{'is_active':False},format='json').status_code==200
    assert not CS.has(user,"VIEW_ALL_REPORTS")
    assert not VisibilityService.reports_queryset(user=user,queryset=Report.objects.all()).exists()

@pytest.mark.django_db
def test_multiple_positions_and_sensitive_scope_defense(setup):
    company,other,admin,user,employee,a,b,foreign,position,client=setup
    first=EmployeePositionAssignment.objects.create(company=company,employee=employee,position=position,scope="BRANCHES")
    first.branches.add(a)
    second=Position.objects.create(company=company,title="Documents officer")
    PositionCapabilityGrant.objects.create(company=company,position=second,capability="MANAGE_DOCUMENTS")
    response=client.post('/api/v1/organizations/position-assignments/',{'employee':employee.pk,'position':second.pk,'scope':'COMPANY','branches':[]},format='json')
    assert response.status_code==201,response.data
    assert CS.has(user,'MANAGE_DOCUMENTS') and CS.has(user,'VIEW_ALL_REPORTS')
    # A malformed/later sensitive grant cannot escape a branch-limited assignment.
    PositionCapabilityGrant.objects.create(company=company,position=position,capability='VIEW_COMPENSATION')
    assert not CS.has(user,'VIEW_COMPENSATION')
    assert client.patch(f"/api/v1/organizations/position-assignments/{first.pk}/",{'scope':'COMPANY','branches':[]},format='json').status_code==403
    employee.status='SUSPENDED';employee.save()
    assert not CS.has(user,'MANAGE_DOCUMENTS') and not CS.has(user,'VIEW_ALL_REPORTS')

@pytest.mark.django_db
def test_position_routing_obeys_locations_and_active_membership(setup):
    from types import SimpleNamespace
    from workflows.services import WorkflowService
    company,other,admin,user,employee,a,b,foreign,position,client=setup
    assignment=EmployeePositionAssignment.objects.create(company=company,employee=employee,position=position,scope='BRANCHES')
    assignment.branches.add(a)
    step=SimpleNamespace(recipient_type='POSITION',recipient_position=position)
    assert WorkflowService.resolve_recipients(step=step,company=company,submitted_by=admin,target=SimpleNamespace(branch_id=a.pk))==[user]
    assert WorkflowService.resolve_recipients(step=step,company=company,submitted_by=admin,target=SimpleNamespace(branch_id=b.pk))==[]
    assignment.is_active=False;assignment.save()
    assert not PositionScope.position_users(company=company,position=position,branch_id=a.pk).exists()

@pytest.mark.django_db
def test_branch_form_eligibility_and_analytics_scope(setup):
    from forms_engine.access import FormAccess
    from forms_engine.services import FormSubmissionService
    from subscriptions.models import Plan,Subscription
    company,other,admin,user,employee,a,b,foreign,position,client=setup
    assignment=EmployeePositionAssignment.objects.create(company=company,employee=employee,position=position,scope='BRANCHES')
    assignment.branches.add(a)
    forms=[]
    for branch in (a,b):
        forms.append(FormTemplate.objects.create(company=company,branch=branch,name=branch.name,code=branch.name,lifecycle_status='PUBLISHED'))
    assert FormAccess.eligible(user,forms[0])
    assert not FormAccess.eligible(user,forms[1])
    submission=FormSubmissionService.create_submission(template=forms[0],user=user)
    assert submission.branch_id==a.pk
    FormSubmission.objects.create(company=company,branch=b,template=forms[1],submitted_by=user,reference_number='outside')
    plan=Plan.objects.create(name='Scope',max_users=10,max_projects=10,price_monthly=0)
    Subscription.objects.create(company=company,plan=plan)
    client.force_authenticate(user)
    response=client.get('/api/v1/analytics/overview/')
    assert response.status_code==200,response.data
    assert sum(response.data['submissions'].values())==1
    assert client.get('/api/v1/organizations/position-assignments/').status_code==403


@pytest.mark.django_db
def test_existing_workflow_recipient_loses_position_access_on_revocation(setup):
    from django.contrib.contenttypes.models import ContentType
    from workflows.models import WorkflowDefinition,WorkflowStepDefinition,WorkflowInstance,WorkflowStepInstance,WorkflowStepRecipient
    from workflows.services import WorkflowService
    company,other,admin,user,employee,a,b,foreign,position,client=setup
    assignment=EmployeePositionAssignment.objects.create(company=company,employee=employee,position=position,scope='BRANCHES')
    assignment.branches.add(a)
    report=Report.objects.create(company=company,branch=a,title='Private',description='x',created_by=admin,visibility='PRIVATE')
    workflow=WorkflowDefinition.objects.create(company=company,name='Review',code='review',target_type='REPORT')
    definition=WorkflowStepDefinition.objects.create(workflow=workflow,order=1,name='Review',recipient_type='POSITION',recipient_position=position)
    instance=WorkflowInstance.objects.create(company=company,workflow=workflow,submitted_by=admin,content_type=ContentType.objects.get_for_model(report),object_id=str(report.pk))
    step=WorkflowStepInstance.objects.create(workflow_instance=instance,definition_step=definition,order=1,name='Review',status='PENDING')
    recipient=WorkflowStepRecipient.objects.create(step=step,user=user,status='PENDING')
    assert WorkflowService.can_act_for_recipient(actor=user,recipient=recipient,permission='APPROVE_REPORTS')
    assignment.is_active=False;assignment.save()
    assert not WorkflowService.can_act_for_recipient(actor=user,recipient=recipient,permission='APPROVE_REPORTS')
    assert not VisibilityService.is_workflow_participant(user=user,obj=report)
    assert not VisibilityService.can_view_report(user,report)
