from rest_framework import serializers

from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "max_users",
            "max_projects",
            "max_branches",
            "storage_limit_bytes",
            "ai_analytics_enabled",
            "reports_enabled",
            "field_operations_enabled",
            "advanced_workflows_enabled",
            "official_records_enabled",
            "custom_forms_enabled",
            "price_monthly",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):

    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        user = getattr(self.context.get("request"), "user", None)
        if user and user.role == "ADMIN" and not user.is_superuser and user.company_id == obj.company_id and obj.is_active:
            return ["CANCEL"]
        return []

    plan = PlanSerializer(
        read_only=True
    )

    plan_id = serializers.PrimaryKeyRelatedField(
        source="plan",
        queryset=Plan.objects.filter(is_active=True),
        write_only=True,
        required=False,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )

    is_valid = serializers.BooleanField(
        read_only=True
    )

    class Meta:
        model = Subscription

        fields = [
            "allowed_actions",
            "id",
            "company",
            "company_name",
            "plan",
            "plan_id",
            "plan_name",
            "is_active",
            "is_valid",
            "started_at",
            "expires_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "company",
            "company_name",
            "plan",
            "plan_name",
            "is_valid",
            "started_at",
            "updated_at",
        ]


# from rest_framework import serializers

# from .models import Plan, Subscription


# class PlanSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = Plan
#         fields = "__all__"


# class SubscriptionSerializer(serializers.ModelSerializer):

#     plan = PlanSerializer(
#         read_only=True
#     )

#     plan_id = serializers.PrimaryKeyRelatedField(
#         source="plan",
#         queryset=Plan.objects.all(),
#         write_only=True,
#         required=False,
#     )

#     class Meta:
#         model = Subscription

#         fields = (
#             "id",
#             "company",

#             "plan",
#             "plan_id",

#             "is_active",

#             "started_at",
#             "expires_at",
#         )

#         read_only_fields = (
#             "id",
#             "company",
#             "started_at",
#         )