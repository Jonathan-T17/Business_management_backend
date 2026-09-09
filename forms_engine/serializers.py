from django.db import transaction

from rest_framework import serializers

from .models import (
    FormTemplate,
    FormField,
    FormSubmission,
)

from .services import (
    FormSubmissionService,
)


# ============================================================
# Form Fields
# ============================================================

class FormFieldSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = FormField

        fields = (
            "id",

            "key",
            "label",
            "help_text",

            "field_type",

            "required",
            "order",

            "options",
            "validation_rules",

            "placeholder",

            "is_active",
        )


# ============================================================
# Form Template
# ============================================================

class FormTemplateSerializer(
    serializers.ModelSerializer
):

    fields = FormFieldSerializer(
        many=True
    )

    class Meta:
        model = FormTemplate

        fields = (
            "id",

            "company",

            "name",
            "code",
            "description",

            "category",

            "branch",
            "department",
            "team",

            "workflow",

            "version",

            "allow_drafts",
            "is_active",
            "lifecycle_status",

            "fields",

            "created_by",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "created_by",
            "version",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):

        request = self.context[
            "request"
        ]

        company = getattr(
            request.user,
            "company",
            None,
        )

        branch = attrs.get(
            "branch"
        )

        department = attrs.get(
            "department"
        )

        team = attrs.get(
            "team"
        )

        workflow = attrs.get(
            "workflow"
        )

        if (
            branch
            and branch.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "branch":
                    "Branch belongs to another company."
            })

        if (
            department
            and department.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "department":
                    "Department belongs to another company."
            })

        if (
            team
            and team.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "team":
                    "Team belongs to another company."
            })

        if (
            workflow
            and workflow.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "workflow":
                    "Workflow belongs to another company."
            })

        if (
            workflow
            and workflow.target_type
            != "FORM_SUBMISSION"
        ):
            raise serializers.ValidationError({
                "workflow":
                    "Workflow must target form submissions."
            })

        return attrs

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):

        fields_data = (
            validated_data.pop(
                "fields"
            )
        )

        template = (
            FormTemplate.objects.create(
                **validated_data
            )
        )

        self._replace_fields(
            template,
            fields_data,
        )

        return template

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):

        fields_data = (
            validated_data.pop(
                "fields",
                None,
            )
        )

        for key, value in (
            validated_data.items()
        ):
            setattr(
                instance,
                key,
                value,
            )

        # Every structural update creates
        # a new template version.
        instance.version += 1

        instance.save()

        if fields_data is not None:
            self._replace_fields(
                instance,
                fields_data,
            )

        return instance

    @staticmethod
    def _replace_fields(
        template,
        fields_data,
    ):

        keys = [
            field["key"]
            for field in fields_data
        ]

        if (
            len(keys)
            != len(set(keys))
        ):
            raise serializers.ValidationError({
                "fields":
                    "Form field keys must be unique."
            })

        template.fields.all().delete()

        for field_data in fields_data:

            FormField.objects.create(
                template=template,
                **field_data,
            )


# ============================================================
# Form Submission
# ============================================================

class FormSubmissionSerializer(
    serializers.ModelSerializer
):

    template_name = serializers.CharField(
        source="template.name",
        read_only=True,
    )

    template_category = serializers.CharField(
        source="template.category",
        read_only=True,
    )

    submitted_by_name = serializers.CharField(
        source="submitted_by.full_name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    team_name = serializers.CharField(
        source="team.name",
        read_only=True,
    )

    class Meta:
        model = FormSubmission

        fields = (
            "id",

            "company",

            "template",
            "template_name",
            "template_category",

            "submitted_by",
            "submitted_by_name",

            "branch",
            "branch_name",

            "department",
            "department_name",

            "team",
            "team_name",

            "project",
            "task",

            "reference_number",
            "title",

            "reporting_date",

            "status",

            "data",

            "schema_snapshot",
            "template_version",

            "submitted_at",
            "approved_at",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "submitted_by",

            "reference_number",

            "status",

            "schema_snapshot",
            "template_version",

            "submitted_at",
            "approved_at",

            "created_at",
            "updated_at",
        )

    def create(
        self,
        validated_data,
    ):

        request = self.context[
            "request"
        ]

        template = (
            validated_data.pop(
                "template"
            )
        )

        return (
            FormSubmissionService
            .create_submission(
                template=template,
                user=request.user,
                **validated_data,
            )
        )

    def update(
        self,
        instance,
        validated_data,
    ):

        if instance.status not in (
            "DRAFT",
            "RETURNED",
        ):
            raise serializers.ValidationError(
                "Only draft or returned submissions "
                "can be edited."
            )

        if (
            instance.submitted_by_id
            != self.context[
                "request"
            ].user.id
        ):
            raise serializers.ValidationError(
                "Only the author can edit this submission."
            )

        data = validated_data.get(
            "data",
            instance.data,
        )

        FormSubmissionService.validate_data(
            template=instance.template,
            data=data,
            partial=True,
        )

        # Template cannot be changed after creation.
        validated_data.pop(
            "template",
            None,
        )

        return super().update(
            instance,
            validated_data,
        )

        if (
            instance.lifecycle_status == "PUBLISHED"
            and instance.submissions.exists()
            and fields_data is not None
        ):
            raise serializers.ValidationError({
                "fields": (
                    "Published forms with submissions cannot be changed. "
                    "Create a new version instead."
                )
            })