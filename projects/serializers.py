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
        fields = [
            "id",
            "project",
            "user",
            "role",
            "joined_at",
        ]
        read_only_fields = ("joined_at",)