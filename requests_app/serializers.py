from rest_framework import serializers

from .models import BusinessRequest

from .services import (
    BusinessRequestService,
)


class BusinessRequestSerializer(
    serializers.ModelSerializer
):

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

        fields = "__all__"

        read_only_fields = (
            "company",
            "requester",
            "request_number",
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

        company = request.user.company

        for name in (
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

        company = request.user.company

        return BusinessRequest.objects.create(
            company=company,

            requester=
                request.user,

            request_number=
                BusinessRequestService
                .generate_number(
                    company=company
                ),

            **validated_data,
        )