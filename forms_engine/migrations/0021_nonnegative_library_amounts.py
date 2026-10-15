from copy import deepcopy
from django.db import migrations

OLD_FIELDS = [{'code': 'payment-collection',
  'field': {'classification': 'NORMAL',
            'field_type': 'DECIMAL',
            'help_text': 'Enter the amount as a number. Use the currency field to identify the '
                         'currency.',
            'key': 'amount',
            'label': 'Amount collected',
            'placeholder': 'Example: 25000',
            'required': True,
            'validation_rules': {'section': 'Collection details'}}},
 {'code': 'collection-summary',
  'field': {'classification': 'NORMAL',
            'field_type': 'DECIMAL',
            'help_text': 'Add the included collections and enter their total as a number.',
            'key': 'total',
            'label': 'Total collected',
            'placeholder': 'Example: 150000',
            'required': True,
            'validation_rules': {'section': 'Collection details'}}},
 {'code': 'expense-request',
  'field': {'classification': 'NORMAL',
            'field_type': 'DECIMAL',
            'help_text': 'Enter the amount as a number. Use the currency field to identify the '
                         'currency.',
            'key': 'amount',
            'label': 'Estimated amount',
            'placeholder': 'Example: 25000',
            'required': True,
            'validation_rules': {'section': 'Form details'}}},
 {'code': 'purchase-request',
  'field': {'classification': 'NORMAL',
            'field_type': 'DECIMAL',
            'help_text': 'Enter your best estimate of the total purchase cost. Leave blank if it '
                         'is not yet known.',
            'key': 'estimated_cost',
            'label': 'Estimated total cost',
            'placeholder': 'Example: 75000',
            'required': False,
            'validation_rules': {'section': 'Form details'}}},
 {'code': 'reimbursement',
  'field': {'classification': 'NORMAL',
            'field_type': 'DECIMAL',
            'help_text': 'Enter the amount as a number. Use the currency field to identify the '
                         'currency.',
            'key': 'amount',
            'label': 'Amount paid',
            'placeholder': 'Example: 25000',
            'required': True,
            'validation_rules': {'section': 'Form details'}}}]

def canonical(field):
    result = dict(field)
    result.pop('order', None)
    for key, default in {'help_text': '', 'placeholder': '', 'classification': 'NORMAL',
                         'required': False, 'options': [], 'validation_rules': {},
                         'is_active': True}.items():
        result.setdefault(key, default)
    return result

def update_catalogue(apps, schema_editor):
    Starter = apps.get_model('forms_engine', 'FormStarter')
    for definition in OLD_FIELDS:
        for starter in Starter.objects.using(schema_editor.connection.alias).filter(code=definition['code']):
            fields = deepcopy(starter.field_schema)
            changed = False
            for field in fields:
                if canonical(field) == canonical(definition['field']):
                    field.setdefault('validation_rules', {})['min'] = 0
                    changed = True
            if changed:
                starter.field_schema = fields
                starter.save(using=schema_editor.connection.alias, update_fields=['field_schema'])

class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0020_formsubmission_client_request_id')]
    operations = [migrations.RunPython(update_catalogue, migrations.RunPython.noop)]
