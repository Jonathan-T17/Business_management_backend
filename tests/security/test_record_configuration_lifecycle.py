from datetime import date
import pytest
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
from companies.models import Company
from company_setup.models import OfficialRecordPolicy
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities
from records_management.models import OfficialRecord
from records_management.finalizer import OfficialRecordFinalizer
from reports.models import Report, ReportField
from reports.services import ReportWorkflowAdapter
from requests_app.models import BusinessRequest
from requests_app.services import BusinessRequestWorkflowAdapter
from planning.models import CompanyPlan
from planning.services import PlanningService
from field_operations.models import FieldActivity
from field_operations.services import FieldOperationService


@pytest.fixture
def record_workspace(django_user_model):
    company=Company.objects.create(name='Issuance lifecycle')
    actor=django_user_model.objects.create_user(email='issuer@example.test',company=company,role='EMPLOYEE')
    UserCapabilityGrant.objects.create(company=company,user=actor,capability=Capabilities.ISSUE_OFFICIAL_RECORDS)
    for source,status in [('REPORT','APPROVED'),('REQUEST','APPROVED'),('PLAN','COMPLETED'),('FIELD_SUMMARY','COMPLETED')]:
        OfficialRecordPolicy.objects.create(company=company,source_type=source,trigger_status=status,prefix=source[:3],automatic_issue=True)
    return company,actor


@pytest.mark.django_db
def test_source_lifecycle_issues_full_records_once(record_workspace):
    company,actor=record_workspace
    report=Report.objects.create(company=company,created_by=actor,title='Private report',description='Details',report_number='R-1',visibility='PRIVATE')
    ReportField.objects.create(report=report,key='observations',value='Source answer')
    ReportWorkflowAdapter.on_approved(target=report,actor=actor,workflow_instance=None)
    request=BusinessRequest.objects.create(company=company,requester=actor,title='Supplies',request_number='REQ-1',request_type='CUSTOM',quantity=3,unit='boxes')
    BusinessRequestWorkflowAdapter.on_approved(target=request,actor=actor,workflow_instance=None)
    plan=CompanyPlan.objects.create(company=company,owner=actor,title='Monthly plan',plan_type='MONTHLY',status='ACTIVE',start_date=date.today(),end_date=date.today())
    PlanningService.transition(plan=plan,user=actor,to_status='COMPLETED')
    activity=FieldActivity.objects.create(company=company,employee=actor,title='Inspection',activity_type='INSPECTION',status='IN_PROGRESS')
    FieldOperationService.complete_activity(activity=activity,user=actor,latitude=1,longitude=2)
    assert OfficialRecord.objects.filter(company=company).count()==4
    records={item.record_type:item for item in OfficialRecord.objects.filter(company=company)}
    assert records['REPORT'].snapshot['fields'][0]['value']=='Source answer'
    assert records['REQUEST'].snapshot['quantity']=='3'
    assert records['PLAN'].snapshot['status']=='COMPLETED'
    assert 'latitude' not in str(records['FIELD_SUMMARY'].snapshot)
    for source in (report,request,plan,activity):
        source.refresh_from_db()
        OfficialRecordFinalizer.finalize(source=source,actor=actor)
    assert OfficialRecord.objects.filter(company=company).count()==4


@pytest.mark.django_db
def test_record_issue_permission_remains_required_and_completion_rolls_back(record_workspace,django_user_model):
    company,_=record_workspace
    owner=django_user_model.objects.create_user(email='plan-owner-no-issue@example.test',company=company,role='EMPLOYEE')
    plan=CompanyPlan.objects.create(company=company,owner=owner,title='Restricted issue',plan_type='MONTHLY',status='ACTIVE',start_date=date.today(),end_date=date.today())
    with pytest.raises(PermissionDenied):
        PlanningService.transition(plan=plan,user=owner,to_status='COMPLETED')
    plan.refresh_from_db();assert plan.status=='ACTIVE'
    assert not OfficialRecord.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_record_rule_rejects_unreachable_statuses_and_normalizes_prefix(django_user_model):
    company=Company.objects.create(name='Record rule validation')
    admin=django_user_model.objects.create_user(email='record-rule-admin@example.test',company=company,role='ADMIN')
    client=APIClient();client.force_authenticate(admin)
    endpoint='/api/v1/company-setup/official-record-policies/'
    for source in ('REPORT','REQUEST','FORM_SUBMISSION','PLAN','FIELD_SUMMARY'):
        invalid=client.post(endpoint,{'source_type':source,'prefix':'BAD','automatic_issue':True,'trigger_status':'DRAFT'},format='json')
        assert invalid.status_code==400,invalid.data
    assert client.post(endpoint,{'source_type':'REPORT','prefix':'../bad','automatic_issue':True,'trigger_status':'APPROVED'},format='json').status_code==400
    result=client.post(endpoint,{'source_type':'PLAN','prefix':' pln ','automatic_issue':True,'trigger_status':'COMPLETED'},format='json')
    assert result.status_code==201,result.data
    assert result.data['prefix']=='PLN'
