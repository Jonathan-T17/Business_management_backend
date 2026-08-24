from rest_framework import serializers
from .models import Project, ProjectMembership

from companies.models import Branch
from users.models import User

from .models import (
    Project,
    ProjectMembership,
)
from .project_roles import ProjectRoles


class ProjectSerializer(serializers.ModelSerializer):

    branches = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        many=True,
        required=False,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    created_by_name = serializers.CharField(
        source="created_by.full_name",
        read_only=True,
    )

    project_scope = serializers.SerializerMethodField()

    class Meta:

        model = Project

        fields = (
            "id",
            "name",
            "description",

            "company",
            "company_name",

            "branches",
            "project_scope",

            "created_by",
            "created_by_name",

            "is_active",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "company_name",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "project_scope",
        )

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request and request.user.is_authenticated:

            user = request.user

            if user.role == "SUPERUSER":
                self.fields[
                    "branches"
                ].queryset = Branch.objects.all()

            elif getattr(user, "company_id", None):

                self.fields[
                    "branches"
                ].queryset = Branch.objects.filter(
                    company_id=user.company_id,
                    is_active=True,
                )

            else:
                self.fields[
                    "branches"
                ].queryset = Branch.objects.none()

        else:
            self.fields[
                "branches"
            ].queryset = Branch.objects.none()

    def get_project_scope(self, obj):

        if not obj.branches.exists():
            return "COMPANY_WIDE"

        return "BRANCH_SCOPED"

    def validate_name(self, value):

        request = self.context["request"]

        company_id = getattr(
            request.user,
            "company_id",
            None,
        )

        queryset = Project.objects.filter(
            company_id=company_id,
            name__iexact=value.strip(),
        )

        if self.instance:
            queryset = queryset.exclude(
                pk=self.instance.pk
            )

        if queryset.exists():

            raise serializers.ValidationError(
                "A project with this name already exists."
            )

        return value.strip()

    def validate_branches(self, branches):

        request = self.context["request"]

        user = request.user

        if user.role == "SUPERUSER":
            return branches

        for branch in branches:

            if branch.company_id != user.company_id:

                raise serializers.ValidationError(
                    "Every branch must belong to your company."
                )

            if not branch.is_active:

                raise serializers.ValidationError(
                    f"Branch '{branch.name}' is inactive."
                )

        return branches


class ProjectMembershipSerializer(
    serializers.ModelSerializer
):

    project_name = serializers.CharField(
        source="project.name",
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

    added_by_name = serializers.CharField(
        source="added_by.full_name",
        read_only=True,
    )

    class Meta:

        model = ProjectMembership

        fields = (
            "id",

            "project",
            "project_name",

            "user",
            "user_name",
            "user_email",

            "role",

            "added_by",
            "added_by_name",

            "joined_at",
        )

        read_only_fields = (
            "added_by",
            "added_by_name",
            "joined_at",
            "project_name",
            "user_name",
            "user_email",
        )

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request and request.user.is_authenticated:

            user = request.user

            if user.role == "SUPERUSER":

                self.fields[
                    "project"
                ].queryset = Project.objects.all()

                self.fields[
                    "user"
                ].queryset = User.objects.all()

            elif getattr(user, "company_id", None):

                self.fields[
                    "project"
                ].queryset = Project.objects.filter(
                    company_id=user.company_id,
                    is_active=True,
                )

                self.fields[
                    "user"
                ].queryset = User.objects.filter(
                    company_id=user.company_id,
                    is_active=True,
                )

            else:

                self.fields[
                    "project"
                ].queryset = Project.objects.none()

                self.fields[
                    "user"
                ].queryset = User.objects.none()

        else:

            self.fields[
                "project"
            ].queryset = Project.objects.none()

            self.fields[
                "user"
            ].queryset = User.objects.none()

    def validate(self, attrs):

        request = self.context["request"]

        project = attrs.get(
            "project",
            getattr(
                self.instance,
                "project",
                None,
            ),
        )

        member_user = attrs.get(
            "user",
            getattr(
                self.instance,
                "user",
                None,
            ),
        )

        role = attrs.get(
            "role",
            getattr(
                self.instance,
                "role",
                None,
            ),
        )

        if not project:
            raise serializers.ValidationError(
                {
                    "project":
                    "Project is required."
                }
            )

        if not member_user:
            raise serializers.ValidationError(
                {
                    "user":
                    "User is required."
                }
            )

        # ----------------------------------------------------
        # Company isolation
        # ----------------------------------------------------

        if (
            request.user.role != "SUPERUSER"
            and project.company_id != request.user.company_id
        ):
            raise serializers.ValidationError(
                {
                    "project":
                    "Project does not belong to your company."
                }
            )

        if member_user.company_id != project.company_id:

            raise serializers.ValidationError(
                {
                    "user":
                    "User must belong to the project's company."
                }
            )

        # ----------------------------------------------------
        # Project branch restrictions
        # ----------------------------------------------------

        if project.branches.exists():

            if not member_user.branch_id:

                raise serializers.ValidationError(
                    {
                        "user":
                        "User must belong to a branch "
                        "assigned to this project."
                    }
                )

            if not project.branches.filter(
                id=member_user.branch_id
            ).exists():

                raise serializers.ValidationError(
                    {
                        "user":
                        "User's branch is not assigned "
                        "to this project."
                    }
                )

        # ----------------------------------------------------
        # Role validation
        # ----------------------------------------------------

        if role not in ProjectRoles.values():

            raise serializers.ValidationError(
                {
                    "role":
                    "Invalid project role."
                }
            )

        # Only one owner.
        if role == ProjectRoles.OWNER.value:

            existing_owner = (
                ProjectMembership.objects.filter(
                    project=project,
                    role=ProjectRoles.OWNER.value,
                )
            )

            if self.instance:
                existing_owner = existing_owner.exclude(
                    pk=self.instance.pk
                )

            if existing_owner.exists():

                raise serializers.ValidationError(
                    {
                        "role":
                        "This project already has an owner."
                    }
                )

        return attrs