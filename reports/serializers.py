from rest_framework import serializers

from companies.models import Branch
from projects.models import Project
from tasks.models import Task

from .models import (
    Report,
    ReportComment,
    ReportField,
)


class ReportFieldSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportField

        fields = [
            "id",
            "key",
            "value",
        ]


class ReportCommentSerializer(serializers.ModelSerializer):

    author_email = serializers.ReadOnlyField(
        source="author.email"
    )

    class Meta:
        model = ReportComment

        fields = [
            "id",
            "report",
            "author",
            "author_email",
            "comment",
            "created_at",
        ]

        read_only_fields = [
            "author",
            "created_at",
        ]


class ReportSerializer(serializers.ModelSerializer):

    fields = ReportFieldSerializer(
        many=True,
        required=False,
    )

    comments = ReportCommentSerializer(
        many=True,
        read_only=True,
    )

    created_by_email = serializers.ReadOnlyField(
        source="created_by.email"
    )

    class Meta:
        model = Report

        fields = [
            "id",
            "title",
            "description",
            "report_type",
            "created_by",
            "created_by_email",
            "company",
            "branch",
            "project",
            "task",
            "visibility",
            "is_anonymous",
            "fields",
            "comments",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_by_email",
            "company",
            "created_at",
            "updated_at",
            "comments",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return

        user = request.user

        if getattr(user, "company", None):
            company = user.company

            self.fields["branch"].queryset = Branch.objects.filter(
                company=company
            )

            self.fields["project"].queryset = Project.objects.filter(
                company=company
            )

            self.fields["task"].queryset = Task.objects.filter(
                company=company
            )

    def validate(self, attrs):
        request = self.context.get("request")

        if not request:
            return attrs

        user = request.user
        company = getattr(user, "company", None)

        if not company:
            raise serializers.ValidationError(
                "User is not associated with a company."
            )

        branch = attrs.get("branch")
        project = attrs.get("project")
        task = attrs.get("task")
        visibility = attrs.get(
            "visibility",
            getattr(
                self.instance,
                "visibility",
                "COMPANY",
            ),
        )

        # --------------------------------------------------
        # Branch isolation
        # --------------------------------------------------

        if branch and branch.company_id != company.id:
            raise serializers.ValidationError({
                "branch": "Branch must belong to your company."
            })

        # --------------------------------------------------
        # Project isolation
        # --------------------------------------------------

        if project and project.company_id != company.id:
            raise serializers.ValidationError({
                "project": "Project must belong to your company."
            })

        # --------------------------------------------------
        # Task isolation
        # --------------------------------------------------

        if task and task.company_id != company.id:
            raise serializers.ValidationError({
                "task": "Task must belong to your company."
            })

        # --------------------------------------------------
        # Project/task consistency
        # --------------------------------------------------

        if task and project:
            if task.project_id != project.id:
                raise serializers.ValidationError({
                    "task": "Task must belong to the selected project."
                })

        # --------------------------------------------------
        # Task automatically determines project
        # --------------------------------------------------

        if task and not project:
            attrs["project"] = task.project

        # --------------------------------------------------
        # Branch/project consistency
        # --------------------------------------------------

        if (
            branch
            and project
            and project.branches.exists()
            and not project.branches.filter(
                id=branch.id
            ).exists()
        ):
            raise serializers.ValidationError({
                "branch": (
                    "Branch is not assigned to the selected project."
                )
            })

        # --------------------------------------------------
        # Visibility requirements
        # --------------------------------------------------

        if visibility == "PROJECT" and not project:
            raise serializers.ValidationError({
                "project": (
                    "A project is required for PROJECT visibility."
                )
            })

        if visibility == "BRANCH" and not branch:
            raise serializers.ValidationError({
                "branch": (
                    "A branch is required for BRANCH visibility."
                )
            })

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Anonymous reports should not expose creator identity.
        if instance.is_anonymous:
            data["created_by"] = None
            data["created_by_email"] = None

        return data

    def create(self, validated_data):
        fields_data = validated_data.pop(
            "fields",
            [],
        )

        report = Report.objects.create(
            **validated_data
        )

        ReportField.objects.bulk_create(
            [
                ReportField(
                    report=report,
                    **field_data,
                )
                for field_data in fields_data
            ]
        )

        return report

    def update(self, instance, validated_data):
        fields_data = validated_data.pop(
            "fields",
            None,
        )

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if fields_data is not None:
            instance.fields.all().delete()

            ReportField.objects.bulk_create(
                [
                    ReportField(
                        report=instance,
                        **field_data,
                    )
                    for field_data in fields_data
                ]
            )

        return instance