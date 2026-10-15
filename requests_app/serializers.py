from rest_framework import serializers

from .models import BusinessRequest

from .services import (
    BusinessRequestService,
)


class BusinessRequestSerializer(
    serializers.ModelSerializer
):

    form_attachment_submission_id = serializers.SerializerMethodField()
    attachment_policy = serializers.SerializerMethodField()
    request_type_policy = serializers.SerializerMethodField()

    def get_request_type_policy(self, obj) -> dict | None:
        from .services import BusinessRequestLifecycleService
        definition = BusinessRequestLifecycleService.resolve_definition(obj)
        if not definition:
            return None
        return {field: getattr(definition, field) for field in ('name', 'amount_enabled', 'amount_required', 'quantity_enabled', 'quantity_required', 'needed_by_enabled', 'needed_by_required')}

    def get_attachment_policy(self, obj) -> dict:
        from .services import BusinessRequestLifecycleService
        definition = BusinessRequestLifecycleService.resolve_definition(obj)
        return {'allowed': bool(definition and definition.attachments_allowed),
                'required': bool(definition and definition.attachments_required)}

    def get_form_attachment_submission_id(self, obj) -> str | None:
        if not obj.form_submission_id:
            return None
        from forms_engine.models import FormSubmission
        from core.visibility import VisibilityService
        if VisibilityService.form_submissions_queryset(user=self.context['request'].user,
                queryset=FormSubmission.objects.filter(pk=obj.form_submission_id)).exists():
            return str(obj.form_submission_id)
        return None

    form_data = serializers.JSONField(write_only=True, required=False)
    form_schema = serializers.SerializerMethodField()
    form_answers = serializers.SerializerMethodField()

    def get_form_schema(self,obj) -> dict | None:
        return obj.form_submission.schema_snapshot if obj.form_submission_id else None

    def get_form_answers(self,obj) -> dict | None:
        from forms_engine.policy import FormSubmissionDisclosurePolicy
        return FormSubmissionDisclosurePolicy.data_for(submission=obj.form_submission,user=self.context['request'].user) if obj.form_submission_id else None

    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from .services import BusinessRequestLifecycleService
        return BusinessRequestLifecycleService.allowed_actions(request_obj=obj, actor=self.context["request"].user)

    requester_name = serializers.CharField(
        source="requester.full_name",
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

    class Meta:
        model = BusinessRequest

        fields = ('request_type_policy', 'attachment_policy', 'form_attachment_submission_id', 'form_data', 'form_schema', 'form_answers', 'allowed_actions', 'id', 'requester_name', 'branch_name', 'department_name', 'request_number', 'request_type', 'request_type_snapshot', 'priority', 'title', 'description', 'amount', 'currency', 'quantity', 'unit', 'needed_by', 'status', 'submitted_at', 'approved_at', 'fulfilled_at', 'created_at', 'updated_at', 'company', 'branch', 'department', 'requester', 'request_type_definition', 'project', 'task', 'workflow')

        read_only_fields = (
            "company",
            "requester",
            "request_number",
            "request_type_snapshot",
            "workflow",
            "status",
            "submitted_at",
            "approved_at",
            "fulfilled_at",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):

        request = self.context[
            "request"
        ]

        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(request.user):
            raise serializers.ValidationError("Tenant company context is required.")
        company = request.user.company

        for name in (
            "request_type_definition",
            "branch",
            "department",
            "project",
            "task",
            "workflow",
        ):
            obj = attrs.get(name)

            if not obj:
                continue

            obj_company = getattr(
                obj,
                "company",
                None,
            )

            if (
                obj_company
                and obj_company.id
                != company.id
            ):
                raise serializers.ValidationError({
                    name:
                        f"{name.title()} belongs "
                        "to another company."
                })

        workflow = attrs.get(
            "workflow"
        )

        if (
            workflow
            and workflow.target_type
            != "REQUEST"
        ):
            raise serializers.ValidationError({
                "workflow":
                    "Workflow must target requests."
            })

        return attrs

    def create(
        self,
        validated_data,
    ):

        request = self.context[
            "request"
        ]

        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(request.user):
            raise serializers.ValidationError("Tenant company context is required.")
        company = request.user.company

        from company_setup.models import RequestTypeDefinition
        from .services import BusinessRequestLifecycleService
        definition = validated_data.pop("request_type_definition", None)
        request_type = validated_data.pop("request_type", "")
        if definition is None:
            definition = RequestTypeDefinition.objects.filter(company=company, code__iexact=request_type, is_active=True).first()
        if definition is None:
            raise serializers.ValidationError({"request_type": "An active request type must be configured."})
        return BusinessRequestLifecycleService.create(actor=request.user, definition=definition, data=validated_data)

    def update(self, instance, validated_data):
        from .services import BusinessRequestLifecycleService
        return BusinessRequestLifecycleService.update(request_obj=instance, actor=self.context["request"].user, data=validated_data)
