from copy import deepcopy
import hashlib
import json
from .models import FormStarter


def snapshot(starter):
    return {'name': starter.name, 'description': starter.description,
            'category': starter.category, 'fields': deepcopy(starter.field_schema)}


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def canonical(field):
    from .versioning import FormTemplateVersionService
    defaults = {'help_text':'', 'placeholder':'', 'classification':'NORMAL', 'required':False,
                'options':[], 'validation_rules':{}, 'is_active':True}
    return {key: deepcopy(field.get(key, defaults.get(key)))
            for key in FormTemplateVersionService.FIELDS if key != 'order'}


def proposal(template):
    from .versioning import FormTemplateVersionService
    starter = FormStarter.objects.filter(code=template.source_starter, is_active=True).first()
    if not starter:
        return None
    latest = snapshot(starter)
    baseline = template.source_starter_snapshot or {}
    current = FormTemplateVersionService.field_data(template)
    old_fields = {field['key']: field for field in baseline.get('fields', [])}
    new_fields = {field['key']: field for field in latest['fields']}
    merged, retained = [], 0
    seen = set()
    for field in current:
        key = field['key']
        seen.add(key)
        if key in old_fields and canonical(field) == canonical(old_fields[key]):
            if key in new_fields:
                merged.append(deepcopy(new_fields[key]))
            # Removing an unchanged stock field is part of the reviewed update.
        else:
            merged.append(field)
            retained += 1
    # A field the company deliberately removed stays removed. Only genuinely
    # new library fields are added when a baseline exists.
    added = [field for field in latest['fields'] if field['key'] not in seen and field['key'] not in old_fields]
    merged.extend(deepcopy(added))
    data = {'source_starter_snapshot': latest}
    for key in ('name', 'description', 'category'):
        if getattr(template, key) == baseline.get(key):
            data[key] = latest[key]
    return {'available': signature(baseline) != signature(latest),
            'linked': True,
            'baseline_missing': not bool(baseline),
            'customized': bool(baseline) and any(field['key'] not in old_fields or canonical(field) != canonical(old_fields[field['key']]) for field in current),
            'changed_fields': [field['label'] for field in current if field['key'] in new_fields and canonical(field) != canonical(new_fields[field['key']])],
            'removed_fields': [field['label'] for field in current if field['key'] in old_fields and field['key'] not in new_fields and canonical(field) == canonical(old_fields[field['key']])],
            'signature': signature({'latest': latest, 'baseline': baseline, 'fields': current,
                                    'updated_at': template.updated_at.isoformat()}),
            'added_fields': [field['label'] for field in added],
            'preserved_fields': retained, 'fields': merged, 'data': data}
