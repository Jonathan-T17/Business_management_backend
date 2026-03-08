from rest_framework import serializers
from .models import Report, ReportField, ReportComment


class ReportFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportField
        fields = ["id", "key", "value"]


class ReportCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.ReadOnlyField(source="author.email")

    class Meta:
        model = ReportComment
        fields = ["id", "author", "author_email", "comment", "created_at"]
        read_only_fields = ["author", "created_at"]


class ReportSerializer(serializers.ModelSerializer):
    fields = ReportFieldSerializer(many=True, required=False)
    comments = ReportCommentSerializer(many=True, read_only=True)

    created_by_email = serializers.ReadOnlyField(source="created_by.email")

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "report_type",
            "description",
            "created_by",
            "created_by_email",
            "company",
            "branch",
            "project",
            "visibility",
            "is_anonymous",
            "fields",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "company",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        fields_data = validated_data.pop("fields", [])

        report = Report.objects.create(**validated_data)

        for field in fields_data:
            ReportField.objects.create(report=report, **field)

        return report