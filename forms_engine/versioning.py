from copy import deepcopy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.data_classification import DataClassification


class FormTemplateVersionService:
    @staticmethod
    def validate_field(field):
        classification = field.get("classification", DataClassification.NORMAL)
        if classification not in DataClassification.VALUES:
            raise ValidationError({"classification": "Invalid data classification."})
        field_type = field.get("field_type") or field.get("type")
        if field_type == "LOCATION" and classification == DataClassification.NORMAL:
            # Explicitly force a security-conscious choice for location fields.
            raise ValidationError({"classification": "Location fields must be classified as PERSONAL or PRECISE_LOCATION."})

    @classmethod
    @transaction.atomic
    def create_draft(cls, *, company, actor, data, fields):
        from forms_engine.models import FormTemplate, FormField

        if not CapabilityService.has(actor, Capabilities.MANAGE_FORM_TEMPLATES):
            raise ValidationError("Form template management permission is required.")
        template = FormTemplate.objects.create(
            company=company,
            created_by=actor,
            lifecycle_status="DRAFT",
            version=1,
            is_active=False,
            **data,
        )
        for order, field in enumerate(fields):
            cls.validate_field(field)
            FormField.objects.create(template=template, order=order, **field)
        return template

    @classmethod
    @transaction.atomic
    def revise(cls, *, template, actor, data, fields=None):
        from forms_engine.models import FormTemplate, FormField

        template = FormTemplate.objects.select_for_update().get(pk=template.pk)
        if template.company_id != actor.company_id:
            raise ValidationError("Cross-company form modification denied.")
        if not CapabilityService.has(actor, Capabilities.MANAGE_FORM_TEMPLATES):
            raise ValidationError("Form template management permission is required.")

        used = template.submissions.exists() or template.lifecycle_status == "PUBLISHED"
        if not used and template.lifecycle_status == "DRAFT":
            target = template
            for key, value in data.items():
                setattr(target, key, value)
            target.save()
            if fields is not None:
                target.fields.all().delete()
                for order, field in enumerate(fields):
                    cls.validate_field(field)
                    FormField.objects.create(template=target, order=order, **field)
            return target

        target = FormTemplate.objects.create(
            company=template.company,
            created_by=actor,
            lifecycle_status="DRAFT",
            version=template.version + 1,
            is_active=False,
            supersedes=template,
            name=data.get("name", template.name),
            code=template.code,
            description=data.get("description", template.description),
            category=data.get("category", template.category),
            branch=data.get("branch", template.branch),
            department=data.get("department", template.department),
            team=data.get("team", template.team),
            workflow=data.get("workflow", template.workflow),
        )
        source_fields = fields if fields is not None else [
            {
                "key": f.key,
                "label": f.label,
                "field_type": f.field_type,
                "required": f.required,
                "help_text": f.help_text,
                "options": deepcopy(f.options),
                "validation_rules": deepcopy(f.validation_rules),
                "placeholder": f.placeholder,
                "classification": getattr(f, "classification", DataClassification.NORMAL),
                "is_active": f.is_active,
            }
            for f in template.fields.order_by("order", "id")
        ]
        for order, field in enumerate(source_fields):
            cls.validate_field(field)
            FormField.objects.create(template=target, order=order, **field)
        return target

    @classmethod
    @transaction.atomic
    def publish(cls, *, template, actor):
        from forms_engine.models import FormTemplate

        template = FormTemplate.objects.select_for_update().get(pk=template.pk)
        if template.company_id != actor.company_id or not CapabilityService.has(actor, Capabilities.PUBLISH_FORM_TEMPLATES):
            raise ValidationError("Form publishing permission is required.")
        if template.lifecycle_status != "DRAFT":
            raise ValidationError("Only draft forms can be published.")
        if not template.fields.filter(is_active=True).exists():
            raise ValidationError("Published forms require at least one active field.")
        FormTemplate.objects.filter(company=template.company, code=template.code, lifecycle_status="PUBLISHED").exclude(pk=template.pk).update(lifecycle_status="ARCHIVED", is_active=False)
        template.lifecycle_status = "PUBLISHED"
        template.is_active = True
        template.save(update_fields=["lifecycle_status", "is_active"])
        return template
