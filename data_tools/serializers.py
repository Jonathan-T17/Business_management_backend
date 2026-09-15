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
        fields = ('id', 'import_type', 'original_filename', 'status', 'total_rows', 'valid_rows', 'invalid_rows', 'created_at', 'completed_at', 'company', 'created_by')
        read_only_fields = (
            "company", "created_by", "status", "total_rows", "valid_rows",
            "invalid_rows", "validation_result", "created_at", "completed_at",
        )


class DataExportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportLog
        fields = ('id', 'export_type', 'format', 'row_count', 'filters', 'created_at', 'company', 'exported_by')
        read_only_fields = fields

class ImportJobStatusSerializer(serializers.ModelSerializer):
    errors = serializers.SerializerMethodField()
    class Meta:
        model = ImportJob
        fields = ('id', 'status', 'total_rows', 'valid_rows', 'invalid_rows', 'errors')
    def get_errors(self, obj):
        return obj.validation_result.get('errors', [])
