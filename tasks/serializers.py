from rest_framework import serializers

from .models import Task, TaskActivity
from projects.models import Project
from users.models import User


class TaskSerializer(serializers.ModelSerializer):

    project_name = serializers.CharField(
        source="project.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.full_name",
        read_only=True,
    )

    assignee_names = serializers.SerializerMethodField()

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task

        fields = [
            "id",
            "company",
            "company_name",
            "project",
            "project_name",
            "title",
            "description",
            "created_by",
            "created_by_name",
            "assignees",
            "assignee_names",
            "status",
            "due_date",
            "is_overdue",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = (
            "company",
            "company_name",
            "created_by",
            "created_by_name",
            "project_name",
            "assignee_names",
            "is_overdue",
            "created_at",
            "updated_at",
        )

    def get_assignee_names(self, obj):
        return [
            user.full_name
            for user in obj.assignees.all()
        ]

    def get_is_overdue(self, obj):
        return obj.is_overdue()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            self.fields["project"].queryset = Project.objects.none()
            self.fields["assignees"].queryset = User.objects.none()
            return

        user = request.user

        if getattr(user, "company_id", None):
            self.fields["project"].queryset = Project.objects.filter(
                company_id=user.company_id,
                is_active=True,
            )

            self.fields["assignees"].queryset = User.objects.filter(
                company_id=user.company_id,
                is_active=True,
            )
        else:
            self.fields["project"].queryset = Project.objects.none()
            self.fields["assignees"].queryset = User.objects.none()

    def validate_project(self, project):
        request = self.context["request"]
        user = request.user

        if user.role != "SUPERUSER":
            if project.company_id != user.company_id:
                raise serializers.ValidationError(
                    "Project does not belong to your company."
                )

        if not project.is_active:
            raise serializers.ValidationError(
                "Cannot create or assign tasks to an inactive project."
            )

        return project

    def validate_assignees(self, assignees):
        request = self.context["request"]
        user = request.user

        for assignee in assignees:

            if assignee.company_id != user.company_id:
                raise serializers.ValidationError(
                    "All assignees must belong to your company."
                )

            if not assignee.is_active:
                raise serializers.ValidationError(
                    f"User {assignee.email} is inactive."
                )

        return assignees

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        project = attrs.get(
            "project",
            getattr(self.instance, "project", None),
        )

        assignees = attrs.get("assignees")

        if not project:
            raise serializers.ValidationError(
                {
                    "project":
                    "A project is required."
                }
            )

        if user.role != "SUPERUSER":
            if project.company_id != user.company_id:
                raise serializers.ValidationError(
                    {
                        "project":
                        "Project does not belong to your company."
                    }
                )

        if assignees is not None:
            project_member_ids = set(
                project.memberships.values_list(
                    "user_id",
                    flat=True,
                )
            )

            invalid_assignees = [
                str(user.id)
                for user in assignees
                if user.id not in project_member_ids
            ]

            if invalid_assignees:
                raise serializers.ValidationError(
                    {
                        "assignees":
                        "All assignees must be members of the project."
                    }
                )

        return attrs


class TaskActivitySerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(
        source="user.full_name",
        read_only=True,
    )

    class Meta:
        model = TaskActivity

        fields = [
            "id",
            "task",
            "user",
            "user_name",
            "action",
            "summary",
            "created_at",
        ]

        read_only_fields = (
            "user",
            "user_name",
            "created_at",
        )