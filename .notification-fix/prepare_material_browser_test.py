from django.db import transaction
from users.models import User
from forms_engine.models import FormStarter,FormTemplate
from forms_engine.serializers import FormFieldSerializer
from forms_engine.versioning import FormTemplateVersionService as Service
from workflows.models import WorkflowDefinition,WorkflowStepDefinition
with transaction.atomic():
    admin=User.objects.get(full_name='Jonathan TWIZE',company_id=3)
    author=User.objects.get(full_name='Honore DUSABAMAHORO',company_id=3)
    manager=User.objects.get(full_name='Uwera Chantal',company_id=3)
    workflow,created=WorkflowDefinition.objects.get_or_create(company=admin.company,code='test-material-journey',defaults={'name':'TEST - Materials branch and headquarters review','target_type':'FORM_SUBMISSION','is_active':True,'created_by':admin})
    if created:
        for order,user,name in [(1,manager,'TEST - Branch manager review'),(2,admin,'TEST - Headquarters approval')]:
            WorkflowStepDefinition.objects.create(workflow=workflow,order=order,name=name,recipient_type='USER',recipient_user=user,notify_email=False)
    for starter_code,label,user in [('material-request','Request',author),('material-dispatch','Dispatch',admin),('material-receipt','Receipt',author),('material-return','Return',author)]:
        code='test-connected-'+starter_code
        template=FormTemplate.objects.filter(company=admin.company,code=code).first()
        if not template:
            starter=FormStarter.objects.get(code=starter_code,is_active=True)
            fields=FormFieldSerializer(data=starter.field_schema,many=True);fields.is_valid(raise_exception=True)
            template=Service.create_draft(company=admin.company,actor=admin,data={'name':'TEST - Materials '+label,'code':code,'starter_code':starter_code,'category':starter.category,'description':'TEST ONLY: Synthetic materials journey. No purchasing, payments or inventory changes.','allow_drafts':True,'branch':author.branch,'audience_user_ids':[str(user.pk)],'workflow':workflow if starter_code=='material-request' else None},fields=fields.validated_data)
        if template.lifecycle_status=='DRAFT': template=Service.publish(template=template,actor=admin)
        print(label,str(template.pk),template.lifecycle_status)
