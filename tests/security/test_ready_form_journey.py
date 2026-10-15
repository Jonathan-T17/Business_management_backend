from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from rest_framework.test import APIClient
from companies.models import Company, Branch
from forms_engine.models import FormStarter, FormTemplate, FormSubmission
from forms_engine.catalogue import snapshot
from forms_engine.versioning import FormTemplateVersionService as Versions
from forms_engine.services import FormSubmissionService
from core.capability_service import CapabilityService as CS

@pytest.fixture
def journey(django_user_model):
    company=Company.objects.create(name='Private company',timezone='Africa/Cairo')
    branch=Branch.objects.create(company=company,name='Food Production')
    admin=django_user_model.objects.create_user(email='admin@ready.test',company=company,role='ADMIN',is_active=True)
    employee=django_user_model.objects.create_user(email='worker@ready.test',full_name='Honore Test',company=company,branch=branch,role='EMPLOYEE',is_active=True)
    peer=django_user_model.objects.create_user(email='peer@ready.test',company=company,branch=branch,role='EMPLOYEE',is_active=True)
    other=Company.objects.create(name='Other private company')
    stranger=django_user_model.objects.create_user(email='stranger@ready.test',company=other,role='ADMIN',is_active=True)
    client=APIClient();client.force_authenticate(admin)
    response=client.post('/api/v1/form-templates/select-starters/',{'codes':['collection-record']},format='json')
    assert response.status_code==201,response.data
    template=FormTemplate.objects.get(pk=response.data['created'][0]['id'])
    assert template.name=='Goods collection form'
    assert template.source_starter_snapshot==snapshot(FormStarter.objects.get(code='collection-record'))
    Versions.publish(template=template,actor=admin)
    return client,admin,employee,peer,stranger,template

@pytest.mark.django_db
def test_opening_uses_company_date_and_profile_without_saving_and_is_tenant_bound(journey):
    client,admin,employee,peer,stranger,template=journey
    client.force_authenticate(employee)
    url=f'/api/v1/form-templates/{template.pk}/initial-values/'
    assert CS.has(employee,'USE_FORMS')
    assert not CS.has_company(employee,'USE_FORMS')
    assert not CS.has(employee,'VIEW_FORM_SUBMISSIONS')
    with patch('django.utils.timezone.now',return_value=datetime(2026,10,3,22,30,tzinfo=timezone.utc)):
        response=client.get(url)
    assert response.status_code==200,response.data
    assert response.data['values']=={'recorded_by':'Honore Test','company_name':'Private company','work_location':'Food Production','collection_date':'2026-10-04'}
    assert response.data['entry_branch']=={'id':employee.branch_id,'name':'Food Production'}
    assert not FormSubmission.objects.exists()
    client.force_authenticate(stranger)
    assert client.get(url).status_code==404
    client.force_authenticate(employee)
    assert client.get(f'/api/v1/form-templates/{template.pk}/?mode=builder').status_code==200
    assert client.patch(f'/api/v1/form-templates/{template.pk}/',{'name':'Forbidden change'},format='json').status_code==403
    assert client.post(f'/api/v1/form-templates/{template.pk}/apply-library-update/',{}).status_code==403

@pytest.mark.django_db
def test_trusted_identity_overrides_spoofing_and_saved_draft_is_stable(journey):
    client,admin,employee,peer,stranger,template=journey
    client.force_authenticate(employee)
    response=client.post('/api/v1/form-submissions/',{'template':str(template.pk),'data':{'recorded_by':'CEO','company_name':'Another company','collection_type':'supplier','items':[{'item':'Paper','quantity':'5','unit':'boxes'}]}},format='json')
    assert response.status_code==201,response.data
    submission=FormSubmission.objects.get(pk=response.data['id'])
    assert submission.data['recorded_by']=='Honore Test'
    assert submission.data['company_name']=='Private company'
    assert submission.data['work_location']=='Food Production'
    date=submission.data['collection_date']
    employee.full_name='Renamed worker';employee.save(update_fields=['full_name'])
    url=f'/api/v1/form-submissions/{submission.pk}/'
    data={**submission.data,'recorded_by':'Someone else','collection_date':'2026-09-01','work_location':'Receiving store'}
    response=client.patch(url,{'data':data},format='json')
    assert response.status_code==200,response.data
    submission.refresh_from_db()
    assert submission.data['recorded_by']=='Honore Test'
    assert submission.data['collection_date']=='2026-09-01' and date
    assert submission.data['work_location']=='Receiving store'
    assert client.post(url+'submit/').status_code==200
    client.force_authenticate(peer)
    assert client.get(url).status_code==404
    client.force_authenticate(stranger)
    assert client.get(url).status_code==404

@pytest.mark.django_db
def test_member_access_respects_restrictions_and_pending_positions(journey):
    client,admin,employee,peer,stranger,template=journey
    from forms_engine.access import FormAccess
    template=Versions.revise(template=template,actor=admin,data={'audience_user_ids':[str(peer.pk)]})
    Versions.publish(template=template,actor=admin)
    assert not FormAccess.eligible(employee,template)
    assert FormAccess.eligible(peer,template)
    peer.position_required=True;peer.save(update_fields=['position_required'])
    assert not FormAccess.eligible(peer,template)
    assert not CS.has(peer,'USE_FORMS')
    peer.position_required=False;peer.is_active=False;peer.save(update_fields=['position_required','is_active'])
    assert not CS.has(peer,'USE_FORMS')

@pytest.mark.django_db
def test_reviewed_updates_keep_custom_fields_history_and_reject_stale_preview(journey):
    client,admin,employee,peer,stranger,template=journey
    starter=FormStarter.objects.get(code='collection-record')
    old_schema=FormSubmissionService.build_schema_snapshot(template)
    draft=Versions.revise(template=template,actor=admin,data={},fields=[{**field,'label':'Our collection notes'} if field['key']=='notes' else field for field in Versions.field_data(template) if field['key']!='company_name']+[{'key':'company_reference','label':'Our reference','field_type':'TEXT'}])
    Versions.publish(template=draft,actor=admin)
    starter.field_schema=deepcopy(starter.field_schema)
    next(field for field in starter.field_schema if field['key']=='notes')['label']='Platform collection notes'
    next(field for field in starter.field_schema if field['key']=='collection_type')['help_text']='Improved collection instructions'
    starter.field_schema.append({'key':'source_reference','label':'Source reference','field_type':'TEXT','required':False})
    starter.save()
    client.force_authenticate(admin)
    url=f'/api/v1/form-templates/{draft.pk}/'
    review=client.get(url).data['library_update']
    assert review['available'] and review['added_fields']==['Source reference']
    # A concurrent library edit invalidates the reviewed proposal.
    starter.description+=' Updated';starter.save()
    assert client.post(url+'apply-library-update/',{'signature':review['signature'],'version':draft.version},format='json').status_code==400
    review=client.get(url).data['library_update']
    updated=client.post(url+'apply-library-update/',{'signature':review['signature'],'version':draft.version},format='json')
    assert updated.status_code==200,updated.data
    revision=FormTemplate.objects.get(pk=updated.data['id'])
    assert revision.pk!=draft.pk and revision.lifecycle_status=='DRAFT'
    assert revision.fields.get(key='notes').label=='Our collection notes'
    assert revision.fields.get(key='collection_type').help_text=='Improved collection instructions'
    assert revision.fields.filter(key='company_reference').exists()
    assert revision.fields.filter(key='source_reference').exists()
    assert not revision.fields.filter(key='company_name').exists()
    draft.refresh_from_db();assert draft.lifecycle_status=='PUBLISHED'
    assert not draft.fields.filter(key='source_reference').exists()
    assert FormSubmissionService.build_schema_snapshot(template)==old_schema
    # Concurrent edits to an unpublished draft also invalidate the review token.
    starter.description+=' Again';starter.save()
    url=f'/api/v1/form-templates/{revision.pk}/'
    review=client.get(url).data['library_update']
    Versions.revise(template=revision,actor=admin,data={'description':'Company instructions'})
    assert client.post(url+'apply-library-update/',{'signature':review['signature'],'version':revision.version},format='json').status_code==400


@pytest.mark.django_db
@pytest.mark.parametrize('source', [['TODAY'], {'type':'TODAY'}, 'UNKNOWN'])
def test_invalid_automatic_sources_are_rejected_without_server_errors(journey,source):
    client,admin,employee,peer,stranger,template=journey
    client.force_authenticate(admin)
    response=client.post('/api/v1/form-templates/',{'name':'Invalid defaults','code':'invalid-defaults','fields':[{'key':'date','label':'Date','field_type':'DATE','validation_rules':{'default_source':source}}]},format='json')
    assert response.status_code==400,response.data
    assert not FormTemplate.objects.filter(code='invalid-defaults').exists()
