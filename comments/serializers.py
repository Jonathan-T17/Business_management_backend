from rest_framework import serializers

from companies.models import Company
from projects.models import Project
from tasks.models import Task

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source="user.email")

    class Meta:
        model = Comment

        fields = [
            "id",
            "company",
            "project",
            "task",
            "user",
            "user_email",
            "content",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "company",
            "user",
            "user_email",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request and request.user.is_authenticated:
            company = getattr(request.user, "company", None)

            if company:
                self.fields["project"].queryset = Project.objects.filter(
                    company=company
                )

                self.fields["task"].queryset = Task.objects.filter(
                    company=company
                )
            else:
                self.fields["project"].queryset = Project.objects.none()
                self.fields["task"].queryset = Task.objects.none()

    def validate_content(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Comment content cannot be empty."
            )

        return value

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        project = attrs.get("project")
        task = attrs.get("task")

        user_company = getattr(user, "company", None)

        if not user_company:
            raise serializers.ValidationError(
                "User is not associated with a company."
            )

        # --------------------------------------------------
        # Company isolation
        # --------------------------------------------------

        if project.company_id != user_company.id:
            raise serializers.ValidationError(
                {
                    "project": (
                        "Project does not belong to your company."
                    )
                }
            )

        # --------------------------------------------------
        # Task validation
        # --------------------------------------------------

        if task:
            if task.company_id != user_company.id:
                raise serializers.ValidationError(
                    {
                        "task": (
                            "Task does not belong to your company."
                        )
                    }
                )

            if task.project_id != project.id:
                raise serializers.ValidationError(
                    {
                        "task": (
                            "Task must belong to the selected project."
                        )
                    }
                )

        # --------------------------------------------------
        # Project membership
        # --------------------------------------------------

        membership_exists = project.memberships.filter(
            user=user
        ).exists()

        # Company administrators/superusers may work with
        # company projects according to the broader authorization
        # layer, while ordinary employees must be project members.
        role = getattr(user, "role", None)

        if not membership_exists and role not in (
            "SUPERUSER",
            "ADMIN",
        ):
            raise serializers.ValidationError(
                {
                    "project": (
                        "You must be a member of the project "
                        "to add comments."
                    )
                }
            )

        return attrs