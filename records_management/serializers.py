from rest_framework import serializers

from .models import OfficialRecord, RecordExport


class RecordExportSerializer(serializers.ModelSerializer):
    exported_by_name = serializers.CharField(
        source="exported_by.full_name",
        read_only=True,
    )

    class Meta:
        model = RecordExport
        fields = "__all__"


class OfficialRecordSerializer(serializers.ModelSerializer):
    issued_by_name = serializers.CharField(
        source="issued_by.full_name",
        read_only=True,
    )

    class Meta:
        model = OfficialRecord
        fields = (
            "id", "record_type", "record_number", "title", "status",
            "source_version", "issued_at", "issued_by", "issued_by_name",
            "supersedes", "void_reason", "voided_at",
            "voided_by", "created_at",
        )
        read_only_fields = fields


class OfficialRecordDetailSerializer(OfficialRecordSerializer):
    class Meta(OfficialRecordSerializer.Meta):
        fields = (*OfficialRecordSerializer.Meta.fields, "snapshot", "approval_snapshot")