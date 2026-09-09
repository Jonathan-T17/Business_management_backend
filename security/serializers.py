from rest_framework import serializers
from .models import ActiveSession, TrustedDevice, AuditLog, LoginHistory

class TrustedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedDevice
        fields = ["id", "device_name", "fingerprint", "ip_address", "last_seen", "created_at", "is_active"]
        read_only_fields = ["fingerprint", "last_seen", "created_at"]


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
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = ActiveSession
        fields = [
            "id", "user", "user_name", "user_email", "browser",
            "operating_system", "device", "ip_address", "last_activity",
            "expires_at", "terminated_at", "is_active",
        ]
        read_only_fields = fields
