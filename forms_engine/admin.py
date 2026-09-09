from django.contrib import admin

from .models import (
    FormTemplate,
    FormField,
    FormSubmission,
)


class FormFieldInline(
    admin.TabularInline
):
    model = FormField
    extra = 0


@admin.register(FormTemplate)
class FormTemplateAdmin(
    admin.ModelAdmin
):

    list_display = (
        "name",
        "company",
        "category",
        "version",
        "is_active",
        "created_at",
    )

    list_filter = (
        "company",
        "category",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "company__name",
    )

    inlines = [
        FormFieldInline
    ]


@admin.register(FormSubmission)
class FormSubmissionAdmin(
    admin.ModelAdmin
):

    list_display = (
        "reference_number",
        "template",
        "company",
        "submitted_by",
        "reporting_date",
        "status",
    )

    list_filter = (
        "company",
        "status",
        "template",
        "reporting_date",
    )

    search_fields = (
        "reference_number",
        "title",
        "submitted_by__email",
    )

    readonly_fields = (
        "schema_snapshot",
        "template_version",
        "created_at",
        "updated_at",
    )