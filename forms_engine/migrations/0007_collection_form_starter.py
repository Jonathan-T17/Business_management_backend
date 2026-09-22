from django.db import migrations

DESIGN = {'code': 'collection-record', 'name': 'Goods or materials collection', 'category': 'COLLECTION', 'allow_drafts': True, 'fields': [{'key': 'collection_date', 'label': 'Collection date', 'field_type': 'DATE', 'required': True, 'classification': 'NORMAL'}, {'key': 'item', 'label': 'Goods or material collected', 'field_type': 'TEXT', 'required': True, 'classification': 'NORMAL'}, {'key': 'quantity', 'label': 'Quantity collected', 'field_type': 'DECIMAL', 'required': True, 'classification': 'NORMAL'}, {'key': 'unit', 'label': 'Unit (for example kg, litres or items)', 'field_type': 'TEXT', 'required': True, 'classification': 'NORMAL'}, {'key': 'notes', 'label': 'Collection notes', 'field_type': 'LONG_TEXT', 'required': False, 'classification': 'NORMAL'}]}

def seed(apps, schema_editor):
    Starter = apps.get_model("forms_engine", "FormStarter")
    Starter.objects.using(schema_editor.connection.alias).get_or_create(
        code=DESIGN["code"], defaults={"name": DESIGN["name"], "category": DESIGN["category"],
        "description": "Record goods or materials collected, quantities and units.", "field_schema": DESIGN["fields"]})

class Migration(migrations.Migration):
    dependencies = [("forms_engine", "0006_formtemplate_audience_user_ids")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
