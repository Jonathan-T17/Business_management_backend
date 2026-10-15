from decimal import Decimal, InvalidOperation
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from security.services import create_audit_log
from .models import MaterialJourney, MaterialMovement, FormTemplate
from .access import FormAccess

STAGES = {'DISPATCH':'material-dispatch','RECEIPT':'material-receipt','RETURN':'material-return'}

def quantity_text(value):
    text=format(Decimal(value),'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def number(value, *, allow_zero=True):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or (not allow_zero and result == 0) or result > Decimal('999999999999') or result.as_tuple().exponent < -6:
            raise ValueError()
        return result
    except (ValueError, InvalidOperation, TypeError):
        raise ValidationError('Use a positive quantity with at most six decimal places.')

def item_list(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        raise ValidationError('Add between one and 100 items.')
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or any(not isinstance(item.get(key),str) or not item[key].strip() or len(item[key]) > 255 for key in ('item','unit')):
            raise ValidationError(f'Item {index + 1} needs its name and unit.')
        try:
            quantity = number(item.get('quantity'),allow_zero=False)
        except ValidationError:
            raise ValidationError(f'Item {index + 1}: use a positive quantity with at most six decimal places.')
        result.append({'id':str(index), 'item':item['item'].strip(), 'unit':item['unit'].strip(), 'quantity':str(quantity)})
    return result

def validate_material_design(code, fields):
    if code not in {'material-request', *STAGES.values()}:
        return
    items = next((field for field in fields if field['key'] == 'items'), None)
    if not items or items['field_type'] != 'ITEM_LIST' or not items.get('required') or items.get('is_active',True) is False or items.get('validation_rules',{}).get('show_when'):
        raise ValidationError({'fields':'Keep the required Items and quantities question for connected material tracking.'})
    if items.get('classification','NORMAL') != 'NORMAL':
        raise ValidationError({'fields':'Material item quantities must remain standard operational information.'})

def initialize(submission):
    if submission.template.source_starter != 'material-request':
        return
    items = item_list(submission.data.get('items'))
    MaterialJourney.objects.update_or_create(submission=submission, defaults={'items':items,'approved':{}})

def totals(journey):
    values = {stage:{item['id']:Decimal('0') for item in journey.items} for stage in STAGES}
    for movement in journey.movements.all():
        for key, quantity in movement.quantities.items():
            values[movement.stage][key] += Decimal(quantity)
    return values

def decision(submission):
    if submission.template.source_starter != 'material-request':
        return
    journey = MaterialJourney.objects.select_for_update().get(submission=submission)
    if not journey.approved:
        journey.approved = {item['id']:item['quantity'] for item in journey.items}
        journey.save(update_fields=['approved'])

def allowed_stages(journey, user):
    from core.position_scope import PositionScope
    if journey.submission.status != 'APPROVED':
        return {}
    templates = FormAccess.templates(user, FormTemplate.objects.filter(source_starter__in=STAGES.values()))
    branch_ids = PositionScope.branches_for(user,'USE_FORMS') | PositionScope.branches_for(user,'SUBMIT_FORMS')
    same_location = user.branch_id == journey.submission.branch_id or journey.submission.branch_id in branch_ids
    return {stage:[{'id':str(form.pk),'name':form.name} for form in templates if form.source_starter == code]
            for stage, code in STAGES.items() if stage == 'DISPATCH' or same_location}

def journey_status(journey, sums=None):
    sums = totals(journey) if sums is None else sums
    complete = journey.submission.status == 'APPROVED'
    for item in journey.items:
        key=item['id']; approved=Decimal(journey.approved.get(key,'0'))
        received=sums['RECEIPT'][key]; returned=sums['RETURN'][key]
        complete = complete and received-returned >= approved
    status = 'Completed' if complete else 'Awaiting delivery' if journey.submission.status == 'APPROVED' else 'Awaiting review'
    if not complete and journey.movements.exists(): status='Partial fulfillment'
    if journey.submission.status in {'RETURNED','REJECTED','CANCELLED'}: status=journey.submission.status.title()
    return status


def representation(journey, user):
    sums = totals(journey)
    items=[]
    for item in journey.items:
        key=item['id']; approved=Decimal(journey.approved.get(key,'0'))
        received=sums['RECEIPT'][key]; returned=sums['RETURN'][key]
        items.append({**item,'approved':quantity_text(approved),'dispatched':quantity_text(sums['DISPATCH'][key]),'received':quantity_text(received),'returned':quantity_text(returned)})
    status = journey_status(journey, sums)
    from workflows.models import WorkflowInstance
    from django.contrib.contenttypes.models import ContentType
    from workflows.presentation import review_context
    instance=WorkflowInstance.objects.filter(company=journey.submission.company,content_type=ContentType.objects.get_for_model(journey.submission),object_id=str(journey.submission.pk),status='IN_PROGRESS').order_by('-started_at','-pk').first()
    can_approve=False
    if instance:
        step=instance.steps.filter(status='PENDING').order_by('order').first()
        can_approve=bool(step and not instance.steps.filter(order__gt=step.order,status='WAITING').exists() and 'APPROVE' in review_context(instance=instance,actor=user)['allowed_actions'])
    return {'reference':journey.submission.reference_number,'status':status,'items':items,'stages':allowed_stages(journey,user),'can_approve':can_approve,
            'history':[{'reference':str(event.reference),'stage':event.stage,'note':event.note,'created_at':event.created_at,
                        'quantities':event.quantities,'related_reference':str(event.related_movement.reference) if event.related_movement_id else None} for event in journey.movements.select_related('related_movement').order_by('created_at','pk')]}

@transaction.atomic
def move(*, submission, actor, stage, template_id, quantities, reference, note='', answers=None, related_reference=None):
    from .services import FormSubmissionService
    journey = MaterialJourney.objects.select_for_update().get(submission=submission)
    if stage not in STAGES or str(template_id) not in {form['id'] for form in allowed_stages(journey,actor).get(stage,[])}:
        raise PermissionDenied('This materials action is not assigned to you.')
    if not isinstance(note,str) or len(note) > 4000:
        raise ValidationError('Keep the note within 4,000 characters.')
    keys={item['id'] for item in journey.items}
    if not isinstance(quantities,dict) or not quantities or set(quantities)-keys:
        raise ValidationError('Choose quantities for the requested items only.')
    amounts={key:quantity_text(number(value)) for key,value in quantities.items()}
    if not any(Decimal(value)>0 for value in amounts.values()):
        raise ValidationError('Enter at least one quantity greater than zero.')
    existing=MaterialMovement.objects.filter(reference=reference).first()
    if existing:
        if existing.journey_id != journey.pk or existing.actor_id != actor.pk or existing.stage != stage or existing.quantities != amounts or str(existing.template_id) != str(template_id) or existing.note != note or (str(existing.related_movement.reference) if existing.related_movement_id else None) != (str(related_reference) if related_reference else None):
            raise ValidationError('This action reference has already been used.')
        return representation(journey,actor)
    related=None
    if stage in {'RECEIPT','RETURN'}:
        related=journey.movements.filter(reference=related_reference,stage='DISPATCH' if stage=='RECEIPT' else 'RECEIPT').first()
        if not related:
            raise ValidationError('Choose the delivery being received or the receipt being returned.')
    sums=totals(journey)
    for key,value in amounts.items():
        approved=Decimal(journey.approved.get(key,'0'))
        ceiling = approved-sums['DISPATCH'][key]+sums['RETURN'][key] if stage=='DISPATCH' else sums['DISPATCH'][key]-sums['RECEIPT'][key] if stage=='RECEIPT' else sums['RECEIPT'][key]-sums['RETURN'][key]
        if Decimal(value)>ceiling:
            raise ValidationError('A quantity exceeds the amount available for this action.')
        if related:
            confirmed=sum((Decimal(event.quantities.get(key,'0')) for event in related.confirmations.all()),Decimal('0'))
            if Decimal(value)>Decimal(related.quantities.get(key,'0'))-confirmed:
                raise ValidationError('A quantity exceeds the remaining amount on the selected delivery or receipt.')
    template=FormTemplate.objects.get(pk=template_id)
    if answers is not None and not isinstance(answers,dict):
        raise ValidationError('Company form answers must be an object.')
    data=dict(answers or {})
    data['items']=[{'item':item['item'],'unit':item['unit'],'quantity':amounts[item['id']]} for item in journey.items if Decimal(amounts.get(item['id'],'0'))>0]
    reference_key='original_reference' if stage=='RETURN' else 'request_reference'
    if template.fields.filter(key=reference_key,is_active=True).exists():
        data[reference_key]=submission.reference_number
    if related and template.fields.filter(key='delivery_reference',is_active=True).exists():
        data['delivery_reference']=str(related.reference)
    from .defaults import apply_defaults
    data = apply_defaults(FormSubmissionService.build_schema_snapshot(template), actor, data)
    FormSubmissionService.validate_data(template=template,data=data)
    event=MaterialMovement.objects.create(journey=journey,actor=actor,template=template,stage=stage,quantities=amounts,
        reference=reference,related_movement=related,note=note,answers=data,schema_snapshot=FormSubmissionService.build_schema_snapshot(template))
    create_audit_log(user=actor,company=submission.company,action='CREATE',obj=event,description=f'Recorded material {stage.lower()} for {submission.reference_number}.')
    return representation(journey,actor)
