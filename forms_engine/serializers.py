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
            "classification",

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

    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from .access import FormAccess
        from core.capabilities import Capabilities as C
        user=self.context['request'].user
        actions=[]
        if FormAccess.has(user,C.MANAGE_FORM_TEMPLATES):
            actions.extend(['UPDATE','COPY'])
        if FormAccess.has(user,C.PUBLISH_FORM_TEMPLATES):
            if obj.lifecycle_status=='DRAFT': actions.append('PUBLISH')
            if obj.lifecycle_status!='ARCHIVED': actions.append('ARCHIVE')
        if FormAccess.eligible(user,obj): actions.append('START')
        return actions

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
            "audience_roles",
            "audience_user_ids",
            "supersedes",
            "allowed_actions",
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
            "supersedes",
            "is_active",
            "lifecycle_status",
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

    def create(self, validated_data):
        from .versioning import FormTemplateVersionService
        fields=validated_data.pop('fields')
        company=validated_data.pop('company', self.context['request'].user.company)
        validated_data.pop('created_by',None)
        return FormTemplateVersionService.create_draft(company=company,actor=self.context['request'].user,data=validated_data,fields=fields)

    def update(self, instance, validated_data):
        from .versioning import FormTemplateVersionService
        fields=validated_data.pop('fields',None)
        return FormTemplateVersionService.revise(template=instance,actor=self.context['request'].user,data=validated_data,fields=fields)


# ============================================================
# Form Submission
# ============================================================

class FormSubmissionSerializer(
    serializers.ModelSerializer
):

    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from .access import FormAccess
        return ['EDIT','SAVE','SUBMIT'] if not hasattr(obj,'business_request') and obj.submitted_by_id==self.context['request'].user.id and obj.status in {'DRAFT','RETURNED'} and FormAccess.can_submit(self.context['request'].user) else []

    def to_representation(self, instance):
        from .policy import FormSubmissionDisclosurePolicy
        result=super().to_representation(instance)
        result['data']=FormSubmissionDisclosurePolicy.data_for(submission=instance,user=self.context['request'].user)
        return result

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
            "allowed_actions",
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

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):

        instance = FormSubmission.objects.select_for_update().get(pk=instance.pk)
        if hasattr(instance,'business_request'):
            raise serializers.ValidationError('Edit this form through its business request.')
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
        from .policy import FormSubmissionDisclosurePolicy
        data = FormSubmissionDisclosurePolicy.restore_masked_answers(
            submission=instance, user=self.context['request'].user, data=data,
        )
        validated_data['data'] = data

        FormSubmissionService.validate_data(
            template=instance.template,
            data=data,
            partial=True,
            schema=instance.schema_snapshot,
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

