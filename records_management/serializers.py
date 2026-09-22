from rest_framework import serializers

from .models import OfficialRecord, RecordExport


class RecordExportSerializer(serializers.ModelSerializer):
    exported_by_name = serializers.CharField(
        source="exported_by.full_name",
        read_only=True,
    )

    class Meta:
        model = RecordExport
        fields = ('id', 'exported_by_name', 'export_format', 'purpose', 'exported_at', 'company', 'record', 'exported_by')


class OfficialRecordSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from core.capabilities import Capabilities
        from core.capability_service import CapabilityService
        request = self.context.get("request")
        if not request:
            return []
        actions = []
        if CapabilityService.has(request.user, Capabilities.EXPORT_OFFICIAL_RECORDS):
            actions.append("EXPORT")
        if obj.status == "ACTIVE" and CapabilityService.has(request.user, Capabilities.VOID_OFFICIAL_RECORDS):
            actions.append("VOID")
        return actions

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
            "voided_by", "created_at", "allowed_actions",
        )
        read_only_fields = fields


class OfficialRecordDetailSerializer(OfficialRecordSerializer):
    # Snapshots stay server-side; source fields may have stricter classifications.
    pass
