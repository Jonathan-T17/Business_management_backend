from django.db import migrations


def restore_selections(apps, schema_editor):
    Template = apps.get_model('forms_engine', 'FormTemplate')
    Field = apps.get_model('forms_engine', 'FormField')
    alias = schema_editor.connection.alias
    groups = Template.objects.using(alias).filter(lifecycle_status='ARCHIVED').values_list('company_id', 'code').distinct()
    for company_id, code in list(groups):
        versions = Template.objects.using(alias).filter(company_id=company_id, code=code)
        if versions.exclude(lifecycle_status='ARCHIVED').exists():
            continue
        previous = versions.order_by('-version').first()
        # A fresh unavailable copy retains historical schemas and entries.
        data = {field.attname: getattr(previous, field.attname) for field in Template._meta.concrete_fields
                if field.name not in {'id', 'created_at', 'updated_at'}}
        data.update(version=previous.version + 1, lifecycle_status='DRAFT', is_active=False,
                    workspace_deleted=False, supersedes_id=previous.pk)
        target = Template.objects.using(alias).create(**data)
        for source in Field.objects.using(alias).filter(template_id=previous.pk):
            values = {field.attname: getattr(source, field.attname) for field in Field._meta.concrete_fields
                      if field.name not in {'id', 'template'}}
            Field.objects.using(alias).create(template_id=target.pk, **values)


class Migration(migrations.Migration):
    dependencies = [('forms_engine', '0018_formtemplate_audience_branch_ids_and_more')]
    operations = [migrations.RunPython(restore_selections, migrations.RunPython.noop)]
