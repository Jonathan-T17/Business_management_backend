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

    def validate(self, attrs):
        from core.capability_service import CapabilityService
        from .access import PlanningAccessService
        user = self.context["request"].user
        if not CapabilityService.is_tenant_identity(user):
            raise serializers.ValidationError("Tenant company context is required.")
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        if not plan or not PlanningAccessService.queryset(user=user, queryset=CompanyPlan.objects.filter(pk=plan.pk)).exists() or not PlanningAccessService.can_manage(user=user, plan=plan):
            raise serializers.ValidationError({"plan": "This plan is not available for editing."})
        if self.instance and "plan" in attrs and plan.pk != self.instance.plan_id:
            raise serializers.ValidationError({"plan": "An existing item cannot be moved to another plan."})
        for field in ("owner", "project", "task"):
            obj = attrs.get(field, getattr(self.instance, field, None))
            if obj and getattr(obj, "company_id", None) != user.company_id:
                raise serializers.ValidationError({field: "Select a record from this company."})
        return attrs

    class Meta:
        model = PlanItem

        fields = ('id', 'owner_name', 'title', 'description', 'target_value', 'actual_value', 'unit', 'status', 'due_date', 'order', 'created_at', 'updated_at', 'plan', 'owner', 'project', 'task')

        read_only_fields = (
            "created_at",
            "updated_at",
        )


class CompanyPlanSerializer(
    serializers.ModelSerializer
):

    allowed_actions = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    completed_items = serializers.SerializerMethodField()
    at_risk_items = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from core.capabilities import Capabilities
        from core.capability_service import CapabilityService
        from .access import PlanningAccessService
        from .services import PlanningService
        user = self.context["request"].user
        if not CapabilityService.has(user, Capabilities.MANAGE_COMPANY_PLANS) or not PlanningAccessService.can_manage(user=user, plan=obj):
            return []
        names = {"ACTIVE": "ACTIVATE", "COMPLETED": "COMPLETE", "CANCELLED": "CANCEL", "ARCHIVED": "ARCHIVE"}
        return [names[state] for state in names if state in PlanningService.TRANSITIONS.get(obj.status, set())]

    def get_total_items(self, obj) -> int:
        return len(obj.items.all())

    def get_completed_items(self, obj) -> int:
        return sum(item.status == "COMPLETED" for item in obj.items.all())

    def get_at_risk_items(self, obj) -> int:
        from django.utils import timezone
        return sum(item.status == "BLOCKED" or (item.status not in {"COMPLETED", "CANCELLED"} and item.due_date is not None and item.due_date < timezone.localdate()) for item in obj.items.all())

    def get_progress(self, obj) -> int:
        total = self.get_total_items(obj)
        return round(100 * self.get_completed_items(obj) / total) if total else 0

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

        fields = ('allowed_actions', 'total_items', 'completed_items', 'at_risk_items', 'progress', 'id', 'items', 'owner_name', 'title', 'description', 'plan_type', 'status', 'visibility', 'start_date', 'end_date', 'created_at', 'updated_at', 'company', 'branch', 'department', 'created_by', 'owner')

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

        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(request.user):
            raise serializers.ValidationError("Tenant company context is required.")
        company = request.user.company
        if "status" in attrs and attrs["status"] != (self.instance.status if self.instance else "DRAFT"):
            raise serializers.ValidationError({"status": "Use the plan lifecycle actions to change status."})
        owner = attrs.get("owner")
        if owner and owner.company_id != company.id:
            raise serializers.ValidationError({"owner": "Owner belongs to another company."})
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})

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