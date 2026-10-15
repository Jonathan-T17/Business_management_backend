import uuid
import pytest
from rest_framework.test import APIClient
from companies.models import Company, Branch
from organizations.models import UserCapabilityGrant
from forms_engine.models import FormTemplate, MaterialMovement
from workflows.models import WorkflowDefinition, WorkflowStepDefinition

@pytest.mark.django_db
def test_material_quantities_permissions_partial_delivery_and_retries(django_user_model):
    company=Company.objects.create(name='Materials company')
    branch=Branch.objects.create(company=company,name='Branch')
    users={name:django_user_model.objects.create_user(email=f'{name}@materials.test',company=company,branch=branch,role='ADMIN' if name=='admin' else 'EMPLOYEE',is_active=True) for name in ['admin','author','reviewer','outsider']}
    for name in ['author','reviewer','outsider']:
        for capability in ['USE_FORMS','SUBMIT_FORMS']:
            UserCapabilityGrant.objects.create(company=company,user=users[name],capability=capability)
    client=APIClient();client.force_authenticate(users['admin'])
    response=client.post('/api/v1/form-templates/select-starters/',{'codes':['material-request','material-dispatch','material-receipt','material-return']},format='json')
    assert response.status_code==201,response.data
    forms={form['source_starter']:form for form in response.data['created']}
    workflow=WorkflowDefinition.objects.create(company=company,name='Materials review',code='materials-review',target_type='FORM_SUBMISSION')
    WorkflowStepDefinition.objects.create(workflow=workflow,name='Headquarters review',order=1,recipient_type='USER',recipient_user=users['reviewer'],notify_email=False)
    for code,form in forms.items():
        url=f'/api/v1/form-templates/{form["id"]}/'
        settings={'workflow':workflow.pk} if code=='material-request' else {'audience_user_ids':[str(users['author'].pk),str(users['reviewer'].pk)]}
        assert client.patch(url,settings,format='json').status_code==200
        published=client.post(url+'publish/')
        assert published.status_code==200,published.data
    client.force_authenticate(users['author'])
    data={'items':[{'item':'Paper','quantity':'10','unit':'boxes'}],'purpose':'Office supplies','needed_by':'2026-10-15','delivery_location':'Branch','priority':'normal'}
    result=client.post('/api/v1/form-submissions/',{'template':forms['material-request']['id'],'data':data},format='json')
    assert result.status_code==201,result.data
    source=f'/api/v1/form-submissions/{result.data["id"]}/'
    assert client.post(source+'submit/').status_code==200
    material=source+'materials/'
    assert client.get(material).data['status']=='Awaiting review'
    payload={'stage':'DISPATCH','template_id':forms['material-dispatch']['id'],'quantities':{'0':'5'},'reference':str(uuid.uuid4()),'answers':{'dispatch_date':'2026-10-02','destination':'Branch'}}
    assert client.post(material,payload,format='json').status_code==403
    client.force_authenticate(users['outsider'])
    assert client.get(material).status_code==404
    assert client.post(source+'approve-materials/',{'quantities':{'0':'5'}},format='json').status_code==404
    client.force_authenticate(users['reviewer'])
    assert client.post(source+'approve-materials/',{'quantities':{'0':'11'}},format='json').status_code==400
    assert client.post(source+'approve-materials/',{'quantities':{'0':'6'}},format='json').status_code==200
    assert client.get(material).data['status']=='Awaiting delivery'
    payload['quantities']={'0':'7'}
    assert client.post(material,payload,format='json').status_code==400
    payload['quantities']={'0':'5'}
    sent=client.post(material,payload,format='json');assert sent.status_code==200,sent.data
    assert client.post(material,payload,format='json').status_code==200
    assert MaterialMovement.objects.count()==1
    client.force_authenticate(users['author'])
    receipt={'stage':'RECEIPT','related_reference':payload['reference'],'template_id':forms['material-receipt']['id'],'quantities':{'0':'6'},'reference':str(uuid.uuid4()),'answers':{'received_date':'2026-10-02','condition':'partial'}}
    assert client.post(material,receipt,format='json').status_code==400
    receipt['quantities']={'0':'5'}
    assert client.post(material,receipt,format='json').status_code==200
    assert client.get(material).data['status']=='Partial fulfillment'
    payload['reference']=str(uuid.uuid4());payload['quantities']={'0':'1'}
    assert client.post(material,payload,format='json').status_code==200
    receipt['reference']=str(uuid.uuid4());receipt['quantities']={'0':'1'}
    receipt['related_reference']=payload['reference']
    completed=client.post(material,receipt,format='json');assert completed.status_code==200,completed.data
    assert completed.data['status']=='Completed'
    returned={'stage':'RETURN','related_reference':receipt['reference'],'template_id':forms['material-return']['id'],'quantities':{'0':'7'},'reference':str(uuid.uuid4()),'answers':{'return_date':'2026-10-02','reason':'Damaged','destination':'Stores'}}
    assert client.post(material,returned,format='json').status_code==400
    returned['quantities']={'0':'1'}
    result=client.post(material,returned,format='json');assert result.status_code==200,result.data
    assert result.data['status']=='Partial fulfillment'
    assert result.data['items'][0]['returned']=='1'
    changed_receipt = {**receipt, 'related_reference':str(uuid.uuid4())}
    assert client.post(material,changed_receipt,format='json').status_code==400
    payload['reference']=str(uuid.uuid4())
    assert client.post(material,payload,format='json').status_code==200
    receipt['reference']=str(uuid.uuid4());receipt['related_reference']=payload['reference']
    replacement=client.post(material,receipt,format='json')
    assert replacement.status_code==200,replacement.data
    assert replacement.data['status']=='Completed'
    foreign=Company.objects.create(name='Other materials company')
    intruder=django_user_model.objects.create_user(email='foreign@materials.test',company=foreign,role='ADMIN',is_active=True)
    client.force_authenticate(intruder)
    assert client.get(material).status_code==404
    assert client.post(material,payload,format='json').status_code==404
