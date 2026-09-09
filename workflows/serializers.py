from django.db import transaction

from rest_framework import serializers

from .models import (
    WorkflowDefinition,
    WorkflowStepDefinition,
    WorkflowInstance,
    WorkflowStepInstance,
    WorkflowStepRecipient,
    WorkflowActionLog,
)


class WorkflowStepDefinitionSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = WorkflowStepDefinition

        fields = (
            "id",
            "name",
            "order",

            "recipient_type",
            "recipient_user",
            "recipient_role",
            "recipient_position",

            "approval_mode",

            "can_reject",
            "can_return",

            "notify_in_app",
            "notify_email",

            "is_required",
        )


class WorkflowDefinitionSerializer(
    serializers.ModelSerializer
):

    steps = (
        WorkflowStepDefinitionSerializer(
            many=True
        )
    )

    class Meta:
        model = WorkflowDefinition

        fields = (
            "id",
            "company",

            "name",
            "code",
            "description",

            "target_type",
            "is_active",

            "steps",

            "created_by",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate_steps(
        self,
        steps,
    ):

        orders = [
            step["order"]
            for step in steps
        ]

        if (
            len(orders)
            != len(set(orders))
        ):
            raise serializers.ValidationError(
                "Workflow step order must be unique."
            )

        return steps

    @transaction.atomic
    def create(
        self,
        validated_data,
    ):

        steps = validated_data.pop(
            "steps"
        )

        workflow = (
            WorkflowDefinition.objects.create(
                **validated_data
            )
        )

        for step in steps:

            WorkflowStepDefinition.objects.create(
                workflow=workflow,
                **step,
            )

        return workflow

    @transaction.atomic
    def update(
        self,
        instance,
        validated_data,
    ):

        steps = validated_data.pop(
            "steps",
            None,
        )

        for key, value in (
            validated_data.items()
        ):
            setattr(
                instance,
                key,
                value,
            )

        instance.save()

        if steps is not None:

            instance.steps.all().delete()

            for step in steps:

                WorkflowStepDefinition.objects.create(
                    workflow=instance,
                    **step,
                )

        return instance


class WorkflowStepRecipientSerializer(
    serializers.ModelSerializer
):

    delegated_from = serializers.SerializerMethodField()

    user_name = serializers.CharField(
        source="user.full_name",
        read_only=True,
    )

    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = WorkflowStepRecipient

        fields = (
            "id",
            "user",
            "user_name",
            "user_email",
            "status",
            "acted_at",
            "note",
            "delegated_from",
        )

    def get_delegated_from(self, obj):
        request = self.context.get("request")
        if not request or obj.user_id == request.user.id:
            return None

        from organizations.models import EmployeeDelegation
        from django.utils import timezone

        if not EmployeeDelegation.objects.filter(
            company=request.user.company,
            from_user_id=obj.user_id,
            to_user=request.user,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
            status__in=["SCHEDULED", "ACTIVE"],
        ).exists():
            return None

        return {
            "id": str(obj.user_id),
            "name": obj.user.full_name,
            "email": obj.user.email,
        }


class WorkflowStepInstanceSerializer(
    serializers.ModelSerializer
):

    recipients = (
        WorkflowStepRecipientSerializer(
            many=True,
            read_only=True,
        )
    )

    class Meta:
        model = WorkflowStepInstance

        fields = (
            "id",
            "order",
            "name",

            "approval_mode",

            "status",

            "started_at",
            "completed_at",

            "recipients",
        )


class WorkflowActionLogSerializer(
    serializers.ModelSerializer
):

    actor_name = serializers.CharField(
        source="actor.full_name",
        read_only=True,
    )

    class Meta:
        model = WorkflowActionLog

        fields = (
            "id",
            "step",
            "actor",
            "actor_name",
            "action",
            "note",
            "metadata",
            "created_at",
        )


class WorkflowInstanceSerializer(
    serializers.ModelSerializer
):

    workflow_name = serializers.CharField(
        source="workflow.name",
        read_only=True,
    )

    submitted_by_name = (
        serializers.CharField(
            source=
                "submitted_by.full_name",
            read_only=True,
        )
    )

    steps = (
        WorkflowStepInstanceSerializer(
            many=True,
            read_only=True,
        )
    )

    action_logs = (
        WorkflowActionLogSerializer(
            many=True,
            read_only=True,
        )
    )

    class Meta:
        model = WorkflowInstance

        fields = (
            "id",

            "company",

            "workflow",
            "workflow_name",

            "content_type",
            "object_id",

            "submitted_by",
            "submitted_by_name",

            "status",

            "started_at",
            "completed_at",

            "steps",
            "action_logs",
        )

        read_only_fields = fields