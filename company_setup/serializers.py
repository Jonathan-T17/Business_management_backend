from rest_framework import serializers

from core.capabilities import Capabilities
from .models import (
    ApprovalRoute, BusinessSetupTemplate, CompanySetupState,
    FieldActivityTemplate, NotificationPolicy, OfficialRecordPolicy,
    ReportingProcess, RequestTypeDefinition, RolePreset,
)


class CompanySetupStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySetupState
        fields = (
            "current_step", "skipped_steps", "completed_steps",
            "selected_template", "onboarding_completed", "updated_at",
        )
        read_only_fields = ("onboarding_completed", "updated_at", "completed_steps", "skipped_steps")


class BusinessSetupTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSetupTemplate
        fields = ("code", "name", "description", "configuration")


class RolePresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePreset
        fields = (
            "id", "company", "code", "name", "description",
            "capabilities", "is_system", "is_active",
        )
        read_only_fields = ("company", "is_system")

    def validate_capabilities(self, capabilities):
        invalid = set(capabilities) - set(Capabilities.values())
        forbidden = set(capabilities) & Capabilities.PLATFORM_ONLY
        if invalid:
            raise serializers.ValidationError(
                f"Invalid capabilities: {', '.join(sorted(invalid))}."
            )
        if forbidden:
            raise serializers.ValidationError(
                "Platform-only capabilities cannot be included in a company preset."
            )
        return sorted(set(capabilities))


class CompanyOwnedConfigurationSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        company = self.context["request"].user.company
        if company is None:
            raise serializers.ValidationError(
                "Company setup requires a tenant company context."
            )
        for field in ("workflow", "form_template"):
            value = attrs.get(field)
            if value and value.company_id != company.id:
                raise serializers.ValidationError(
                    {field: "This item belongs to another company."}
                )
        template=attrs.get('form_template')
        if template and (template.lifecycle_status!='PUBLISHED' or not template.is_active):
            raise serializers.ValidationError({'form_template':'Choose an active published form version.'})
        return attrs


class RequestTypeDefinitionSerializer(CompanyOwnedConfigurationSerializer):
    class Meta:
        model = RequestTypeDefinition
        fields = (
            "id", "company", "code", "name", "description", "icon", "sensitive",
            "amount_enabled", "amount_required", "quantity_enabled",
            "quantity_required", "needed_by_enabled", "needed_by_required",
            "attachments_allowed", "attachments_required", "workflow",
            "form_template", "is_active",
        )
        read_only_fields = ("company",)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'code' in attrs:
            duplicates = RequestTypeDefinition.objects.filter(company=self.context['request'].user.company, code__iexact=attrs['code'])
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({'code': 'This reference code is already used. Choose another code.'})
        workflow = attrs.get('workflow')
        if workflow and (workflow.target_type != 'REQUEST' or not workflow.is_active):
            raise serializers.ValidationError({'workflow': 'Choose an active approval route for requests.'})
        for enabled, required in (
            ("amount_enabled", "amount_required"),
            ("quantity_enabled", "quantity_required"),
            ("needed_by_enabled", "needed_by_required"),
            ("attachments_allowed", "attachments_required"),
        ):
            if attrs.get(required, getattr(self.instance, required, False)) and not attrs.get(
                enabled, getattr(self.instance, enabled, False)
            ):
                raise serializers.ValidationError(
                    {required: "A required field must be enabled."}
                )
        return attrs


class RequestTypeChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    sensitive = serializers.BooleanField()
    amount_enabled = serializers.BooleanField()
    amount_required = serializers.BooleanField()
    quantity_enabled = serializers.BooleanField()
    quantity_required = serializers.BooleanField()
    needed_by_enabled = serializers.BooleanField()
    needed_by_required = serializers.BooleanField()
    attachments_allowed = serializers.BooleanField()
    attachments_required = serializers.BooleanField()
    form_template_id = serializers.UUIDField(allow_null=True)


class RequestApprovalChoiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class FieldActivityTemplateSerializer(CompanyOwnedConfigurationSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        for field in ('require_location', 'require_photo', 'require_signature', 'require_notes'):
            if attrs.get(field) and not getattr(self.instance, field, False):
                raise serializers.ValidationError({field: 'Use required fields in a published field form. This legacy flag is not enforced by stop completion.'})
        return attrs

    class Meta:
        model = FieldActivityTemplate
        fields = (
            "id", "company", "name", "activity_type", "require_arrival",
            "require_completion", "require_location", "require_photo",
            "require_signature", "require_notes", "form_template", "is_active",
        )
        read_only_fields = ("company",)


class ApprovalRouteSerializer(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalRoute
        fields = (
            "id", "company", "name", "description", "workflow",
            "is_active", "steps",
        )
        read_only_fields = ("company", "workflow", "steps")

    def get_steps(self, instance):
        return [
            {
                "name": step.name,
                "order": step.order,
                "recipient_type": step.recipient_type,
                "recipient_user": step.recipient_user_id,
                "recipient_role": step.recipient_role,
                "recipient_position": step.recipient_position_id,
                "approval_mode": step.approval_mode,
                "can_reject": step.can_reject,
                "can_return": step.can_return,
                "notify_in_app": step.notify_in_app,
                "notify_email": step.notify_email,
            }
            for step in instance.workflow.steps.all()
        ]


class ReportingProcessSerializer(serializers.ModelSerializer):
    template = serializers.UUIDField(source="schedule.template_id", read_only=True)
    approval_route_name = serializers.CharField(
        source="approval_route.name", read_only=True
    )

    class Meta:
        model = ReportingProcess
        fields = (
            "id", "company", "name", "description", "schedule", "template",
            "approval_route", "approval_route_name", "is_active",
        )
        read_only_fields = ("company", "schedule", "template")


class OfficialRecordPolicySerializer(serializers.ModelSerializer):
    SOURCE_STATUSES = {
        'REPORT': ('APPROVED',),
        'REQUEST': ('APPROVED', 'FULFILLED'),
        'FORM_SUBMISSION': ('APPROVED',),
        'PLAN': ('COMPLETED',),
        'FIELD_SUMMARY': ('COMPLETED',),
    }

    def validate_prefix(self, value):
        value = value.strip().upper()
        if not value or not value.replace('-', '').isalnum():
            raise serializers.ValidationError('Use letters, numbers and hyphens for the record prefix.')
        return value

    def validate(self, attrs):
        current = self.instance
        source = attrs.get('source_type', getattr(current, 'source_type', None))
        status = attrs.get('trigger_status', getattr(current, 'trigger_status', None))
        active = attrs.get('is_active', getattr(current, 'is_active', True))
        automatic = attrs.get('automatic_issue', getattr(current, 'automatic_issue', False))
        if active and automatic and status not in self.SOURCE_STATUSES.get(source, ()):
            raise serializers.ValidationError({'trigger_status': 'Choose a supported issuance status for this source type.'})
        return attrs

    class Meta:
        model = OfficialRecordPolicy
        fields = (
            "id", "company", "source_type", "prefix", "automatic_issue",
            "trigger_status", "is_active",
        )
        read_only_fields = ("company",)


class NotificationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPolicy
        fields = (
            "id", "company", "event_code", "in_app_enabled", "email_enabled",
            "user_can_disable_email", "is_active",
        )
        read_only_fields = ("company",)
