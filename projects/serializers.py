from rest_framework import serializers
from .models import Project, ProjectMembership
from companies.models import Branch


class ProjectSerializer(serializers.ModelSerializer):
    branches = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "company",
            "branches",
            "created_by",
            "is_active",
            "created_at",
        ]
        read_only_fields = ("company", "created_by")


class ProjectMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMembership
        fields = "__all__"
        read_only_fields = ("added_by",)

    def validate(self, data):
        request = self.context["request"]
        project = data["project"]
        role_to_assign = data["role"]

        try:
            my_membership = ProjectMembership.objects.get(
                project=project,
                user=request.user
            )
        except ProjectMembership.DoesNotExist:
            raise serializers.ValidationError(
                "You are not a member of this project."
            )

        if my_membership.role == "MANAGER" and role_to_assign != "MEMBER":
            raise serializers.ValidationError(
                "Managers can only add members."
            )

        if my_membership.role == "MEMBER":
            raise serializers.ValidationError(
                "Members cannot add users."
            )

        return data