import pytest
from rest_framework.test import APIClient
from companies.models import Company
from forms_engine.models import FormStarter, FormTemplate
from forms_engine.serializers import FormFieldSerializer
from forms_engine.versioning import FormTemplateVersionService
from forms_engine.starters import STARTERS


@pytest.mark.django_db
def test_library_designs_are_valid_and_selection_is_tenant_owned(django_user_model):
    company = Company.objects.create(name='Library company')
    other = Company.objects.create(name='Other library company')
    admin = django_user_model.objects.create_user(email='library@forms.test', company=company, role='ADMIN', is_active=True)
    employee = django_user_model.objects.create_user(email='worker@forms.test', company=company, role='EMPLOYEE', is_active=True)
    client = APIClient()
    for design in STARTERS:
        fields = FormFieldSerializer(data=design['fields'], many=True)
        assert fields.is_valid(), fields.errors
        FormTemplateVersionService.validate(actor=None, company=None, data={}, fields=fields.validated_data, starter=True)
        assert FormStarter.objects.filter(code=design['code']).exists()
    client.force_authenticate(employee)
    url = '/api/v1/form-templates/select-starters/'
    assert client.post(url, {'codes':['material-request']}, format='json').status_code == 403
    client.force_authenticate(admin)
    assert client.post(url, {'codes':['material-request', 'does-not-exist']}, format='json').status_code == 400
    assert not FormTemplate.objects.filter(company=company).exists()
    response = client.post(url, {'codes':['material-request', 'material-receipt', 'material-request']}, format='json')
    assert response.status_code == 201, response.data
    assert len(response.data['created']) == 2
    assert not FormTemplate.objects.filter(company=other).exists()
    assert all(form['lifecycle_status'] == 'DRAFT' and form['workflow'] is None for form in response.data['created'])
    assert not FormTemplate.objects.filter(company=company, is_active=True).exists()
    response = client.post(url, {'codes':['material-request', 'material-receipt']}, format='json')
    assert response.status_code == 200 and len(response.data['existing']) == 2
    assert FormTemplate.objects.filter(company=company).count() == 2
    target = FormTemplate.objects.get(company=company, code='material-request')
    assert client.post(f'/api/v1/form-templates/{target.pk}/publish/').status_code == 400
    copied = client.post(f'/api/v1/form-templates/{target.pk}/copy/', {'name':'Copied request','code':'copied-request'},format='json')
    assert copied.status_code == 201, copied.data
    assert copied.data['source_starter'] == 'material-request'
    question = target.fields.first()
    question.label = 'Company wording'
    question.save()
    assert FormStarter.objects.get(code='material-request').field_schema[0]['label'] != 'Company wording'


@pytest.mark.django_db
def test_library_selection_rolls_back_invalid_platform_design(django_user_model):
    company = Company.objects.create(name='Atomic library')
    admin = django_user_model.objects.create_user(email='atomic@forms.test', company=company, role='ADMIN', is_active=True)
    FormStarter.objects.create(code='broken-choice', name='Invalid choice', field_schema=[
        {'key':'choice','label':'Choice','field_type':'SELECT','options':[]}])
    client = APIClient(); client.force_authenticate(admin)
    response = client.post('/api/v1/form-templates/select-starters/', {'codes':['daily-report', 'broken-choice']}, format='json')
    assert response.status_code == 400, response.data
    assert not FormTemplate.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_position_audience_and_headquarters_route_are_explicit(django_user_model):
    from companies.models import Branch
    from organizations.models import Position, EmployeeProfile, UserCapabilityGrant
    from forms_engine.access import FormAccess
    from workflows.models import WorkflowDefinition
    company = Company.objects.create(name='Routed company')
    headquarters = Branch.objects.create(company=company, name='Head office')
    company.headquarters = headquarters; company.save()
    branch = Branch.objects.create(company=company, name='Branch')
    admin = django_user_model.objects.create_user(email='routes@forms.test', company=company, role='ADMIN', is_active=True)
    manager = django_user_model.objects.create_user(email='manager@forms.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    peer = django_user_model.objects.create_user(email='peer@forms.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    position = Position.objects.create(company=company, branch=branch, title='Branch manager', primary_scope='BRANCH')
    headquarters_position = Position.objects.create(company=company, branch=headquarters, title='Head of operations', primary_scope='COMPANY')
    EmployeeProfile.objects.create(company=company, user=manager, employee_id='M-1', branch=branch, position=position)
    for user in (manager, peer):
        UserCapabilityGrant.objects.create(company=company, user=user, capability='USE_FORMS')
    client = APIClient(); client.force_authenticate(admin)
    created = client.post('/api/v1/form-templates/select-starters/', {'codes':['branch-summary']}, format='json').data['created'][0]
    url = f'/api/v1/form-templates/{created["id"]}/'
    route = {'route':'HEADQUARTERS', 'headquarters_position':headquarters_position.pk}
    assert client.post(url+'configure-review/', route, format='json').status_code == 400
    assert not WorkflowDefinition.objects.filter(company=company).exists()
    assert client.patch(url, {'audience_position_ids':[position.pk]}, format='json').status_code == 200
    configured = client.post(url+'configure-review/', route, format='json')
    assert configured.status_code == 200, configured.data
    definition = WorkflowDefinition.objects.get(pk=configured.data['workflow'])
    assert definition.is_active and definition.steps.get().recipient_position_id == headquarters_position.pk
    assert configured.data['review_preview']['steps'][0]['destination'] == headquarters_position.title
    assert configured.data['review_preview']['warnings']
    assert client.patch(url, {'audience_position_ids':[]}, format='json').status_code == 400
    response = client.post(url+'publish/', {'audience':'COMPANY'}, format='json')
    assert response.status_code == 200, response.data
    assert response.data['audience_position_ids'] == [position.pk]
    template = FormTemplate.objects.get(pk=created['id'])
    assert FormAccess.eligible(manager, template)
    assert not FormAccess.eligible(peer, template)
    foreign = Company.objects.create(name='Foreign routes')
    foreign_position = Position.objects.create(company=foreign, title='Foreign leader')
    response = client.post(url+'configure-review/', {'route':'HEADQUARTERS','headquarters_position':foreign_position.pk}, format='json')
    assert response.status_code == 400
    assert WorkflowDefinition.objects.filter(company=company).count() == 1
    revised = client.post(url+'configure-review/', {'route':'SUPERVISOR'}, format='json')
    assert revised.status_code == 200 and revised.data['id'] != created['id']
    template.refresh_from_db()
    assert template.workflow_id == definition.pk and template.lifecycle_status == 'PUBLISHED'


@pytest.mark.django_db
def test_supervisor_route_uses_saved_position_reporting_line(django_user_model):
    from types import SimpleNamespace
    from companies.models import Branch
    from organizations.models import Position, EmployeeProfile
    from workflows.services import WorkflowService
    company = Company.objects.create(name='Supervisor structure')
    branch = Branch.objects.create(company=company, name='Branch')
    manager_position = Position.objects.create(company=company, branch=branch, title='Branch manager', primary_scope='BRANCH')
    staff_position = Position.objects.create(company=company, branch=branch, title='Staff', primary_scope='BRANCH', reports_to=manager_position)
    staff = django_user_model.objects.create_user(email='staff@structure.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    manager = django_user_model.objects.create_user(email='lead@structure.test', company=company, branch=branch, role='EMPLOYEE', is_active=True)
    for user, position, code in ((staff,staff_position,'STAFF'),(manager,manager_position,'LEAD')):
        EmployeeProfile.objects.create(company=company, branch=branch, user=user, position=position, employee_id=code)
    recipients = WorkflowService.resolve_recipients(step=SimpleNamespace(recipient_type='REPORTER_MANAGER'), company=company,
        submitted_by=staff, target=SimpleNamespace(branch_id=branch.pk))
    assert [user.pk for user in recipients] == [manager.pk]
    manager_position.is_active = False; manager_position.save()
    assert not WorkflowService.resolve_recipients(step=SimpleNamespace(recipient_type='REPORTER_MANAGER'), company=company,
        submitted_by=staff, target=SimpleNamespace(branch_id=branch.pk))



@pytest.mark.django_db
def test_ready_made_forms_have_answer_guidance_and_plain_language():
    for design in STARTERS:
        assert design.get('description'), design['code']
        assert all(field.get('help_text') for field in design['fields']), design['code']
    daily = next(item for item in STARTERS if item['code'] == 'daily-report')
    assert {'report_date','work_completed','blockers','next_steps','recorded_by','company_name','work_location'} == {field['key'] for field in daily['fields']}
    difficulties = next(field for field in daily['fields'] if field['key'] == 'blockers')
    assert difficulties['label'] == 'Difficulties and support needed'
    assert not difficulties['required']
    assert difficulties['placeholder'].startswith('Example:')
    assert FormStarter.objects.get(code='daily-report').field_schema == daily['fields']


@pytest.mark.django_db
def test_catalogue_refinement_preserves_company_copies_and_operator_changes():
    from importlib import import_module
    from django.apps import apps
    from django.db import connection
    migration = import_module('forms_engine.migrations.0014_plain_language_form_library')
    company = Company.objects.create(name='Preserved company')
    existing = FormTemplate.objects.create(company=company,name='Our daily report',code='daily-report')
    starter = FormStarter.objects.get(code='daily-report')
    starter.description = 'Our platform-specific instructions'
    starter.save()
    original_fields = starter.field_schema
    with connection.schema_editor() as editor:
        migration.update_catalogue(apps, editor)
    starter.refresh_from_db()
    existing.refresh_from_db()
    assert starter.description == 'Our platform-specific instructions'
    assert starter.field_schema == original_fields
    assert existing.name == 'Our daily report'
    assert not existing.fields.exists()


@pytest.mark.django_db
def test_removed_selection_can_be_chosen_again_without_restoring_company_changes(django_user_model):
    company = Company.objects.create(name='Reset library company')
    admin = django_user_model.objects.create_user(email='reset@forms.test', company=company, role='ADMIN', is_active=True)
    client = APIClient(); client.force_authenticate(admin)
    url = '/api/v1/form-templates/select-starters/'
    result = client.post(url, {'codes':['daily-report']}, format='json')
    original = FormTemplate.objects.get(pk=result.data['created'][0]['id'])
    original.name = 'Old company title'; original.audience_roles = ['MANAGER']; original.save()
    FormTemplateVersionService.retire(template=original, actor=admin)
    result = client.post(url, {'codes':['daily-report']}, format='json')
    assert result.status_code == 201, result.data
    fresh = FormTemplate.objects.get(pk=result.data['created'][0]['id'])
    original.refresh_from_db()
    assert original.lifecycle_status == 'ARCHIVED'
    assert fresh.pk != original.pk and fresh.version == original.version + 1
    assert fresh.lifecycle_status == 'DRAFT' and not fresh.is_active
    assert fresh.name == FormStarter.objects.get(code='daily-report').name
    assert fresh.audience_roles == [] and fresh.workflow_id is None
    assert fresh.supersedes_id == original.pk
    again = client.post(url, {'codes':['daily-report']}, format='json')
    assert again.status_code == 200 and again.data['existing'][0]['id'] == str(fresh.pk)
