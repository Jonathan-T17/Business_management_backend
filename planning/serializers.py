from rest_framework import serializers

from .models import (
    CompanyPlan,
    PlanItem,
)


class PlanItemSerializer(
    serializers.ModelSerializer
):

    owner_name = serializers.CharField(
        source="owner.full_name",
        read_only=True,
    )

    class Meta:
        model = PlanItem

        fields = "__all__"

        read_only_fields = (
            "created_at",
            "updated_at",
        )


class CompanyPlanSerializer(
    serializers.ModelSerializer
):

    items = PlanItemSerializer(
        many=True,
        read_only=True,
    )

    owner_name = serializers.CharField(
        source="owner.full_name",
        read_only=True,
    )

    class Meta:
        model = CompanyPlan

        fields = "__all__"

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

        branch = attrs.get("branch")
        department = attrs.get(
            "department"
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
            attrs.get("start_date")
            and attrs.get("end_date")
            and attrs["start_date"]
            > attrs["end_date"]
        ):
            raise serializers.ValidationError({
                "end_date":
                    "End date must be after start date."
            })

        return attrs