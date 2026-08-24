from rest_framework import serializers

from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(
        source="user.email"
    )

    user_name = serializers.SerializerMethodField()

    action_display = serializers.CharField(
        source="get_action_display",
        read_only=True,
    )

    class Meta:
        model = ActivityLog

        fields = [
            "id",
            "company",
            "project",
            "task",
            "user",
            "user_email",
            "user_name",
            "action",
            "action_display",
            "metadata",
            "created_at",
        ]

        read_only_fields = fields

    def get_user_name(self, obj):
        if not obj.user:
            return None

        if hasattr(obj.user, "get_full_name"):
            name = obj.user.get_full_name()

            if name:
                return name

        return getattr(
            obj.user,
            "email",
            None,
        )