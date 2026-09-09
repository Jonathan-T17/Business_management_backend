from rest_framework import serializers

from .models import (
    ReportingSchedule,
    ReportingObligation,
)


class ReportingScheduleSerializer(
    serializers.ModelSerializer
):

    template_name = serializers.CharField(
        source="template.name",
        read_only=True,
    )

    class Meta:
        model = ReportingSchedule

        fields = (
            "id",
            "company",

            "name",
            "description",

            "template",
            "template_name",

            "frequency",

            "target_type",
            "target_user",
            "target_role",
            "target_branch",
            "target_department",
            "target_team",
            "target_position",

            "due_time",
            "weekday",
            "day_of_month",

            "custom_rule",

            "start_date",
            "end_date",

            "allow_late_submission",
            "is_active",

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

    def validate(self, attrs):

        request = self.context[
            "request"
        ]

        company = request.user.company

        template = attrs.get(
            "template"
        )

        if (
            template
            and template.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "template":
                    "Template belongs to another company."
            })

        target_type = attrs.get(
            "target_type"
        )

        frequency = attrs.get(
            "frequency"
        )

        if (
            frequency == "WEEKLY"
            and attrs.get(
                "weekday"
            ) is None
        ):
            raise serializers.ValidationError({
                "weekday":
                    "Weekday is required."
            })

        if (
            frequency == "MONTHLY"
            and attrs.get(
                "day_of_month"
            ) is None
        ):
            raise serializers.ValidationError({
                "day_of_month":
                    "Day of month is required."
            })

        if (
            target_type == "USER"
            and not attrs.get(
                "target_user"
            )
        ):
            raise serializers.ValidationError({
                "target_user":
                    "Target user is required."
            })

        if (
            target_type == "ROLE"
            and not attrs.get(
                "target_role"
            )
        ):
            raise serializers.ValidationError({
                "target_role":
                    "Target role is required."
            })

        return attrs


class ReportingObligationSerializer(
    serializers.ModelSerializer
):

    schedule_name = serializers.CharField(
        source="schedule.name",
        read_only=True,
    )

    template = serializers.UUIDField(
        source="schedule.template_id",
        read_only=True,
    )

    template_name = serializers.CharField(
        source="schedule.template.name",
        read_only=True,
    )

    user_name = serializers.CharField(
        source="user.full_name",
        read_only=True,
    )

    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = ReportingObligation

        fields = (
            "id",

            "company",

            "schedule",
            "schedule_name",

            "template",
            "template_name",

            "user",
            "user_name",
            "user_email",

            "reporting_date",
            "due_at",

            "status",

            "submission",

            "created_at",
            "submitted_at",
        )

        read_only_fields = fields