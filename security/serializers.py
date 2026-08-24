from rest_framework import serializers
from .models import TrustedDevice, AuditLog, LoginHistory

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
