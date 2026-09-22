from copy import deepcopy
from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError, PermissionDenied
from core.capabilities import Capabilities as C
from core.data_classification import DataClassification
from security.services import create_audit_log
from .access import FormAccess

class FormTemplateVersionService:
    FIELDS = ('key','label','help_text','field_type','required','order','options','validation_rules','placeholder','classification','is_active')
    CONFIG = ('name','code','description','category','branch','department','team','workflow','allow_drafts','audience_roles','audience_user_ids')

    @classmethod
    def authorize(cls, actor, company, capability=C.MANAGE_FORM_TEMPLATES):
        if actor.company_id != company.pk or not FormAccess.has(actor, capability):
            raise PermissionDenied('Form configuration permission is required in this company.')

    @classmethod
    def validate(cls, *, actor, company, data, fields, starter=False):
        from django.contrib.auth import get_user_model
        people = data.get('audience_user_ids', [])
        if not isinstance(people, list) or any(not isinstance(pk, str) for pk in people):
            raise ValidationError({'audience_user_ids': 'Choose company users from the list.'})
        if people:
            eligible = {str(pk) for pk in get_user_model().objects.filter(company=company, is_active=True, role__in=['ADMIN', 'MANAGER', 'EMPLOYEE']).values_list('pk', flat=True)}
            if any(pk not in eligible for pk in people):
                raise ValidationError({'audience_user_ids': 'Choose active users in this company.'})
        roles=data.get('audience_roles',[])
        if not isinstance(roles,list) or any(r not in {'ADMIN','MANAGER','EMPLOYEE'} for r in roles):
            raise ValidationError({'audience_roles':'Choose company roles only.'})
        for key in ('branch','department','team','workflow'):
            obj=data.get(key)
            if obj and obj.company_id != company.pk:
                raise ValidationError({key:'Choose an item in this company.'})
        workflow=data.get('workflow')
        if workflow and workflow.target_type != 'FORM_SUBMISSION':
            raise ValidationError({'workflow':'Choose a form-submission workflow.'})
        keys=[f['key'] for f in fields]
        if len(keys)!=len(set(keys)):
            raise ValidationError({'fields':'Field keys must be unique.'})
        previous_keys=set()
        for field in fields:
            rules = field.get('validation_rules', {})
            if not isinstance(rules, dict):
                raise ValidationError({'validation_rules': 'Use an object for question validation rules.'})
            condition=rules.get('show_when')
            if condition and (not isinstance(condition,dict) or condition.get('field') not in previous_keys or not isinstance(condition.get('equals'),(str,int,float,bool))):
                raise ValidationError({'validation_rules':'Conditional questions must reference an earlier field and an expected answer.'})
            previous_keys.add(field['key'])
            classification=field.get('classification','NORMAL')
            if classification not in DataClassification.VALUES:
                raise ValidationError({'classification':'Unknown field classification.'})
            if classification in DataClassification.SENSITIVE and not starter and not FormAccess.has(actor,C.CONFIGURE_SENSITIVE_FORMS):
                raise PermissionDenied('Sensitive form configuration permission is required.')
            if field['field_type']=='LOCATION' and classification not in {'PERSONAL','PRECISE_LOCATION'}:
                raise ValidationError({'classification':'Classify location fields as PERSONAL or PRECISE_LOCATION.'})
            if field['field_type'] in {'SELECT','MULTISELECT'}:
                options=field.get('options',[])
                if not isinstance(options,list) or not options or any(not isinstance(o,dict) or not o.get('value') or not o.get('label') for o in options):
                    raise ValidationError({'options':'Choices need a value and label.'})

    @classmethod
    def field_data(cls, template):
        return [{key:deepcopy(getattr(field,key)) for key in cls.FIELDS} for field in template.fields.all()]

    @classmethod
    def write_fields(cls, target, fields):
        from .models import FormField
        for order, field in enumerate(fields):
            payload={k:v for k,v in field.items() if k in cls.FIELDS}
            payload['order']=order
            FormField.objects.create(template=target,**payload)

    @classmethod
    @transaction.atomic
    def create_draft(cls, *, company, actor, data, fields):
        from .models import FormTemplate
        cls.authorize(actor,company)
        type(company).objects.select_for_update().get(pk=company.pk)
        cls.validate(actor=actor,company=company,data=data,fields=fields)
        if FormTemplate.objects.filter(company=company,code=data['code']).exists():
            raise ValidationError({'code':'This form code is already in use. Revise the existing form or use a new code.'})
        target=FormTemplate.objects.create(company=company,created_by=actor,is_active=False,lifecycle_status='DRAFT',**data)
        cls.write_fields(target,fields)
        cls.audit(target,actor,'Created form draft')
        return target

    @classmethod
    @transaction.atomic
    def revise(cls, *, template, actor, data, fields=None):
        from .models import FormTemplate
        cls.authorize(actor,template.company)
        type(template.company).objects.select_for_update().get(pk=template.company_id)
        template=FormTemplate.objects.select_for_update().get(pk=template.pk)
        config={key:getattr(template,key) for key in cls.CONFIG}
        config.update(data)
        if config['code'] != template.code:
            raise ValidationError({'code':'Use copy to create a different form code.'})
        fields=cls.field_data(template) if fields is None else fields
        cls.validate(actor=actor,company=template.company,data=config,fields=fields)
        if template.lifecycle_status=='DRAFT' and not template.submissions.exists():
            target=template
            for key,value in config.items(): setattr(target,key,value)
            target.save()
            target.fields.all().delete()
        else:
            if FormTemplate.objects.filter(company=template.company,code=template.code,lifecycle_status='DRAFT').exclude(pk=template.pk).exists():
                raise ValidationError('A draft revision already exists. Edit that draft.')
            version=FormTemplate.objects.filter(company=template.company,code=template.code).aggregate(value=Max('version'))['value']+1
            target=FormTemplate.objects.create(company=template.company,created_by=actor,supersedes=template,version=version,lifecycle_status='DRAFT',is_active=False,**config)
        cls.write_fields(target,fields)
        cls.audit(target,actor,'Saved form draft revision')
        return target

    @classmethod
    @transaction.atomic
    def publish(cls, *, template, actor):
        from .models import FormTemplate
        cls.authorize(actor,template.company,C.PUBLISH_FORM_TEMPLATES)
        type(template.company).objects.select_for_update().get(pk=template.company_id)
        template=FormTemplate.objects.select_for_update().get(pk=template.pk)
        if template.lifecycle_status!='DRAFT': raise ValidationError('Only draft forms can be published.')
        fields=cls.field_data(template)
        if not any(f['is_active'] for f in fields): raise ValidationError('Add at least one active field.')
        config={key:getattr(template,key) for key in cls.CONFIG}
        cls.validate(actor=actor,company=template.company,data=config,fields=fields)
        if template.workflow and not template.workflow.is_active:
            raise ValidationError({'workflow':'Activate the approval workflow before publishing this form.'})
        FormTemplate.objects.filter(company=template.company,code=template.code,lifecycle_status='PUBLISHED').exclude(pk=template.pk).update(lifecycle_status='ARCHIVED',is_active=False)
        template.lifecycle_status='PUBLISHED';template.is_active=True;template.save()
        cls.audit(template,actor,'Published form version')
        return template

    @classmethod
    @transaction.atomic
    def retire(cls, *, template, actor):
        cls.authorize(actor,template.company,C.PUBLISH_FORM_TEMPLATES)
        template=type(template).objects.select_for_update().get(pk=template.pk)
        template.lifecycle_status='ARCHIVED';template.is_active=False;template.save()
        cls.audit(template,actor,'Retired form version')
        return template

    @classmethod
    def copy(cls, *, template, actor, code, name):
        cls.authorize(actor,template.company)
        return cls.create_draft(company=actor.company,actor=actor,data={'name':name,'code':code,'category':template.category,'description':template.description,'allow_drafts':template.allow_drafts},fields=cls.field_data(template))

    @staticmethod
    def audit(template,actor,description):
        create_audit_log(user=actor,company=template.company,action='UPDATE',obj=template,description=description,metadata={'version':template.version})
