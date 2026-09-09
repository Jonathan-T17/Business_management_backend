from rest_framework import serializers

from .models import ImportJob, DataExportLog


class SearchResultSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(allow_blank=True)
    url = serializers.CharField(allow_blank=True)
    status = serializers.CharField(allow_null=True, required=False)


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = "__all__"
        read_only_fields = (
            "company", "created_by", "status", "total_rows", "valid_rows",
            "invalid_rows", "validation_result", "created_at", "completed_at",
        )


class DataExportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportLog
        fields = "__all__"
        read_only_fields = fields