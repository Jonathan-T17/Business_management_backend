from rest_framework import serializers
from .models import ActiveSession, TrustedDevice, AuditLog, LoginHistory

class TrustedDeviceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="device_name", read_only=True)
    last_used_at = serializers.DateTimeField(source="last_seen", read_only=True)
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        return ["REVOKE"] if request and obj.user_id == request.user.pk and obj.is_active else []

    class Meta:
        model = TrustedDevice
        fields = ["id", "name", "last_used_at", "allowed_actions", "device_name", "user_agent_summary", "ip_address", "last_seen", "created_at", "is_active"]
        read_only_fields = ["user_agent_summary", "ip_address", "last_seen", "created_at", "is_active"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "user", "action", "status", "description", "ip_address", "created_at"]
        read_only_fields = fields


class LoginHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginHistory
        fields = ["id", "user", "ip_address", "user_agent", "successful", "failure_reason", "created_at"]
        read_only_fields = fields


class CompanyAuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "user", "user_name", "action", "severity", "status",
            "object_type", "object_id", "description", "created_at",
        ]
        read_only_fields = fields


class ActiveSessionSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        return ["REVOKE"] if request and obj.user_id == request.user.pk and obj.is_active else []

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = ActiveSession
        fields = [
            "id", "allowed_actions", "user", "user_name", "user_email", "browser",
            "operating_system", "device", "ip_address", "last_activity",
            "expires_at", "terminated_at", "is_active",
        ]
        read_only_fields = fields
