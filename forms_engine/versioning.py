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
    CONFIG = ('name','code','description','category','branch','department','team','workflow','allow_drafts','audience_roles','audience_user_ids','audience_position_ids','audience_branch_ids','entry_visibility','share_confidential','source_starter','source_starter_snapshot')

    @classmethod
    def authorize(cls, actor, company, capability=C.MANAGE_FORM_TEMPLATES):
        if actor.company_id != company.pk or not FormAccess.has(actor, capability):
            raise PermissionDenied('Form configuration permission is required in this company.')

    @classmethod
    def validate(cls, *, actor, company, data, fields, starter=False):
        from companies.models import Branch
        branches = data.get('audience_branch_ids', [])
        if not isinstance(branches, list) or any(type(pk) is not int for pk in branches) or set(branches) - set(Branch.objects.filter(company=company, is_active=True, pk__in=branches).values_list('pk', flat=True)):
            raise ValidationError({'audience_branch_ids': 'Choose active branches in this company.'})
        if data.get('share_confidential') and not FormAccess.has(actor, C.CONFIGURE_SENSITIVE_FORMS):
            raise PermissionDenied('Confidential form access authority is required.')
        from django.contrib.auth import get_user_model
        from organizations.models import Position
        positions = data.get('audience_position_ids', [])
        if not isinstance(positions, list) or any(type(pk) is not int for pk in positions):
            raise ValidationError({'audience_position_ids':'Choose positions from this company.'})
        if positions and set(positions) - set(Position.objects.filter(company=company, is_active=True, pk__in=positions).values_list('pk', flat=True)):
            raise ValidationError({'audience_position_ids':'Choose active positions in this company.'})
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
        if workflow and workflow.code.startswith('form-review-') and workflow.description == 'Company form route: HEADQUARTERS' and not (people or positions):
            raise ValidationError({'audience_position_ids':'Direct headquarters reporting needs permitted positions or people. Keep this restriction or choose a supervisor review route.'})
        keys=[f['key'] for f in fields]
        if len(keys)!=len(set(keys)):
            raise ValidationError({'fields':'Field keys must be unique.'})
        previous_keys=set()
        previous_fields={}
        for field in fields:
            rules = field.get('validation_rules', {})
            if not isinstance(rules, dict):
                raise ValidationError({'validation_rules': 'Use an object for question validation rules.'})
            from .validation import validate_rules
            from django.core.exceptions import ValidationError as RuleError
            try:
                validate_rules(rules)
            except RuleError as exc:
                raise ValidationError({'validation_rules': f"{field['label']}: {exc.messages[0]}"})
            from .defaults import SOURCES, LOCKED
            source = rules.get('default_source')
            if source is not None and (not isinstance(source, str) or (source and (source not in SOURCES or field['field_type'] != SOURCES[source]))):
                raise ValidationError({'validation_rules':'Choose a compatible automatic value for this field.'})
            if source in LOCKED and field.get('classification', 'NORMAL') != 'PERSONAL':
                raise ValidationError({'classification':'Automatic identity fields must be classified as PERSONAL.'})
            if 'section' in rules and (not isinstance(rules['section'],str) or len(rules['section']) > 100):
                raise ValidationError({'validation_rules':'Section names must be text up to 100 characters.'})
            condition=rules.get('show_when')
            if condition and (not isinstance(condition,dict) or condition.get('field') not in previous_keys or not isinstance(condition.get('equals'),(str,int,float,bool))):
                raise ValidationError({'validation_rules':'Conditional questions must reference an earlier field and an expected answer.'})
            if condition:
                source_field = previous_fields[condition['field']]
                if source_field['field_type'] in {'ITEM_LIST', 'LOCATION', 'MULTISELECT'}:
                    raise ValidationError({'validation_rules':'Choose an earlier single-answer question for a condition.'})
                if source_field['field_type'] == 'BOOLEAN' and str(condition['equals']).lower() not in {'true', 'false'}:
                    raise ValidationError({'validation_rules':'Choose Yes or No for this condition.'})
                if source_field['field_type'] == 'SELECT' and condition['equals'] not in [option['value'] for option in source_field.get('options', [])]:
                    raise ValidationError({'validation_rules':'Choose a saved answer from the earlier question.'})
            if field.get('is_active', True):
                previous_keys.add(field['key'])
                previous_fields[field['key']]=field
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
                values = [o['value'] for o in options]
                if any(not isinstance(value, str) for value in values) or len(values) != len(set(values)):
                    raise ValidationError({'options':'Each choice needs a unique text value.'})

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
        data = dict(data)
        starter = data.pop('starter_code', '')
        if starter:
            from .models import FormStarter
            catalogue = FormStarter.objects.filter(code=starter, is_active=True).first()
            if not catalogue:
                raise ValidationError({'starter_code':'Choose an available system template.'})
            from .catalogue import snapshot
            data['source_starter'] = starter
            data['source_starter_snapshot'] = snapshot(catalogue)
        from .materials import validate_material_design
        validate_material_design(data.get('source_starter',''), fields)
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
        config.pop('starter_code', None)
        from .materials import validate_material_design
        validate_material_design(config.get('source_starter',''), fields if fields is not None else cls.field_data(template))
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
    def publish(cls, *, template, actor, publication=None):
        from .models import FormTemplate
        cls.authorize(actor,template.company,C.PUBLISH_FORM_TEMPLATES)
        type(template.company).objects.select_for_update().get(pk=template.company_id)
        template=FormTemplate.objects.select_for_update().get(pk=template.pk)
        if template.lifecycle_status!='DRAFT': raise ValidationError('Only draft forms can be published.')
        if publication is not None:
            if template.submissions.exists():
                raise ValidationError('This form already has entries. Prepare a revision before changing publication access.')
            scope = publication['audience']
            branches = publication.get('branch_ids', [])
            if scope == 'HEADQUARTERS':
                branches = [template.company.headquarters_id] if template.company.headquarters_id else []
            if scope != 'COMPANY' and not branches:
                raise ValidationError({'branch_ids': 'Choose at least one location. Set up headquarters before choosing headquarters only.'})
            if scope == 'COMPANY': branches = []
            preserve = publication.get('preserve_restrictions', True)
            ordinary_restrictions = bool(template.branch_id or template.department_id or template.team_id or template.audience_roles or template.audience_user_ids or template.audience_position_ids)
            broadens_locations = bool(template.audience_branch_ids) and (not branches or bool(set(template.audience_branch_ids) - set(branches)))
            if (broadens_locations or (ordinary_restrictions and not preserve)) and not publication.get('confirm_audience_change'):
                raise ValidationError({'confirm_audience_change': 'Review and confirm the broader audience before publishing.'})
            share = publication.get('share_confidential', False)
            if share and (not FormAccess.has(actor, C.CONFIGURE_SENSITIVE_FORMS) or not publication.get('confirm_confidential_access')):
                raise PermissionDenied('Confidential access authority and explicit confirmation are required.')
            if share and publication['entry_visibility'] != 'AUDIENCE':
                raise ValidationError('Choose the published audience before sharing confidential answers.')
            template.audience_branch_ids = branches
            template.entry_visibility = publication['entry_visibility']
            template.share_confidential = share
            direct_headquarters = (template.workflow and template.workflow.code.startswith('form-review-')
                                   and template.workflow.description == 'Company form route: HEADQUARTERS')
            # Direct headquarters reporting remains an expressly authorized
            # exception to the normal location-based publication audience.
            if not preserve:
                template.branch = template.department = template.team = None
                if not direct_headquarters:
                    template.audience_roles = []; template.audience_user_ids = []; template.audience_position_ids = []
        fields=cls.field_data(template)
        from .materials import validate_material_design
        validate_material_design(template.source_starter, fields)
        if template.source_starter == 'material-request' and not template.workflow_id:
            raise ValidationError({'workflow':'Choose a review route before publishing material requests.'})
        if template.category == 'REQUEST' and template.source_starter and not template.workflow_id and not (publication and publication.get('confirm_no_approval')):
            raise ValidationError({'confirm_no_approval': 'Choose an approval route, or explicitly confirm that this request needs no approval.'})
        if template.source_starter in {'material-dispatch','material-receipt','material-return'} and template.workflow_id:
            raise ValidationError({'workflow':'Review belongs to the original material request. Delivery and receipt are confirmations by the authorized positions.'})
        if not any(f['is_active'] for f in fields): raise ValidationError('Add at least one active field.')
        config={key:getattr(template,key) for key in cls.CONFIG}
        cls.validate(actor=actor,company=template.company,data=config,fields=fields)
        if template.workflow and not template.workflow.steps.exists():
            raise ValidationError({'workflow':'Add at least one review step before publishing this form.'})
        if template.workflow and not template.workflow.is_active:
            raise ValidationError({'workflow':'Activate the approval workflow before publishing this form.'})
        FormTemplate.objects.filter(company=template.company,code=template.code,lifecycle_status='PUBLISHED').exclude(pk=template.pk).update(lifecycle_status='ARCHIVED',is_active=False)
        template.lifecycle_status='PUBLISHED';template.is_active=True;template.save()
        cls.audit(template,actor,'Published form version')
        if publication is not None:
            create_audit_log(user=actor, company=template.company, action='UPDATE', obj=template,
                description='Configured form publication audience and answer access.', metadata={'audience':publication['audience'], 'branches':template.audience_branch_ids, 'entry_visibility':template.entry_visibility, 'share_confidential':template.share_confidential, 'confirmed':bool(publication.get('confirm_confidential_access')), 'preserved_restrictions':publication.get('preserve_restrictions', True), 'confirmed_audience_change':bool(publication.get('confirm_audience_change')), 'confirmed_no_approval':bool(publication.get('confirm_no_approval'))})
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
    @transaction.atomic
    def delete_from_workspace(cls, *, template, actor):
        cls.authorize(actor, template.company, C.PUBLISH_FORM_TEMPLATES)
        type(template.company).objects.select_for_update().get(pk=template.company_id)
        # Keep immutable definitions and entries for historical review, but remove
        # the entire selected form from the workspace and prevent new entries.
        type(template).objects.filter(company=template.company, code=template.code).update(workspace_deleted=True, lifecycle_status='ARCHIVED', is_active=False)
        cls.audit(template, actor, 'Deleted form from company workspace; historical entries retained')

    @classmethod
    def copy(cls, *, template, actor, code, name):
        cls.authorize(actor,template.company)
        return cls.create_draft(company=actor.company,actor=actor,data={'name':name,'code':code,'category':template.category,'description':template.description,'allow_drafts':template.allow_drafts,'source_starter':template.source_starter,'source_starter_snapshot':template.source_starter_snapshot},fields=cls.field_data(template))

    @staticmethod
    def audit(template,actor,description):
        create_audit_log(user=actor,company=template.company,action='UPDATE',obj=template,description=description,metadata={'version':template.version})
