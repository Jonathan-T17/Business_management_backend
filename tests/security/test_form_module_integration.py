import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from companies.models import Company
from forms_engine.models import FormTemplate, FormField
from company_setup.models import RequestTypeDefinition, FieldActivityTemplate
from requests_app.models import BusinessRequest
from field_operations.models import FieldActivity, FieldStop
from organizations.models import UserCapabilityGrant
from core.capabilities import Capabilities as C
from forms_engine.versioning import FormTemplateVersionService

@pytest.mark.django_db
def test_request_and_field_use_shared_forms(django_user_model, settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr("subscriptions.services.SubscriptionService.can_upload", lambda *args, **kwargs: True)
    company=Company.objects.create(name='Form modules')
    user=django_user_model.objects.create_user(email='worker@form.test',company=company,role='ADMIN')
    template=FormTemplate.objects.create(company=company,name='Inspection',code='inspection',is_active=False)
    FormField.objects.create(template=template,key='findings',label='Findings',field_type='TEXT',required=True)
    FormTemplateVersionService.publish(template=template,actor=user)
    template.refresh_from_db()
    definition=RequestTypeDefinition.objects.create(company=company,name='Custom request',code='custom-inspection',form_template=template)
    client=APIClient();client.force_authenticate(user)
    response=client.post('/api/v1/business-requests/',{'request_type':definition.code,'title':'Request','description':'Inspect vehicle','form_data':{'findings':'Check vehicle'}},format='json')
    assert response.status_code==201,response.data
    obj=BusinessRequest.objects.get(pk=response.data['id'])
    assert obj.form_submission.template_id==template.pk
    assert response.data['form_answers']['findings']=='Check vehicle'
    assert client.post(f'/api/v1/form-submissions/{obj.form_submission_id}/submit/').status_code==400
    from django.core.files.uploadedfile import SimpleUploadedFile
    from requests_app.services import BusinessRequestLifecycleService
    from rest_framework.exceptions import ValidationError
    definition.attachments_required=True;definition.save()
    with pytest.raises(ValidationError):
        BusinessRequestLifecycleService.validate_definition(obj)
    attachment_url=f'/api/v1/form-submissions/{obj.form_submission_id}/attachments/'
    response=client.post(attachment_url, {'file':SimpleUploadedFile('inspection.txt', b'checked')})
    assert response.status_code==201,response.data
    BusinessRequestLifecycleService.validate_definition(obj)
    attachment_id=response.data["id"]
    definition.attachments_allowed=False;definition.attachments_required=False;definition.save()
    assert client.post(attachment_url, {'file':SimpleUploadedFile('blocked.txt', b'blocked')}).status_code==403
    assert client.delete(f'{attachment_url}{attachment_id}/').status_code==204
    configuration=FieldActivityTemplate.objects.create(company=company,name='Inspection',activity_type='INSPECTION',form_template=template)
    activity=FieldActivity.objects.create(company=company,employee=user,title='Visit',activity_type='INSPECTION',activity_date=timezone.localdate())
    stop=FieldStop.objects.create(activity=activity,sequence=1,stop_type='OTHER',location_name='Site')
    root=f'/api/v1/field-stops/{stop.pk}/'
    assert client.post(root+'complete/').status_code==400
    response=client.post(root+'start-form/',{'configuration':configuration.pk})
    assert response.status_code==201,response.data
    submission=response.data['id'];url=f'/api/v1/form-submissions/{submission}/'
    assert client.post(url+'submit/').status_code==400
    assert client.patch(url,{'data':{'findings':'All checked'}},format='json').status_code==200
    assert client.post(url+'submit/').status_code==200
    assert client.post(root+'complete/').status_code==200
