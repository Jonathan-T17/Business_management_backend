from rest_framework import serializers

from companies.models import Branch
from organizations.models import Department, Team
from projects.models import Project
from users.models import User

from .models import Conversation, ConversationMember, Message


class ConversationMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ConversationMember
        fields = (
            "id", "user", "user_name", "user_email", "joined_at",
            "last_read_at", "unread_count",
        )
        read_only_fields = fields

    def get_unread_count(self, obj):
        messages = obj.conversation.messages.filter(deleted_at__isnull=True)
        if obj.last_read_at:
            messages = messages.filter(created_at__gt=obj.last_read_at)
        return messages.exclude(sender=obj.user).count()


class ConversationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    memberships = ConversationMemberSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id", "company", "company_name", "name", "scope", "branch",
            "department", "team", "project", "created_by", "created_by_name",
            "created_at", "updated_at", "memberships", "unread_count",
        )
        read_only_fields = (
            "id", "company", "company_name", "created_by", "created_by_name",
            "created_at", "updated_at", "memberships", "unread_count",
        )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user
        scope_fields = {
            "BRANCH": ("branch", Branch),
            "DEPARTMENT": ("department", Department),
            "TEAM": ("team", Team),
            "PROJECT": ("project", Project),
        }
        scope = attrs.get("scope", getattr(self.instance, "scope", None))
        if scope in scope_fields:
            field, _ = scope_fields[scope]
            target = attrs.get(field, getattr(self.instance, field, None))
            if target is None or target.company_id != user.company_id:
                raise serializers.ValidationError({field: "Must belong to your company."})
        for field in ("branch", "department", "team", "project"):
            target = attrs.get(field)
            if target is not None and target.company_id != user.company_id:
                raise serializers.ValidationError({field: "Must belong to your company."})
        return attrs

    def get_unread_count(self, obj):
        request = self.context["request"]
        membership = obj.memberships.filter(user=request.user).first()
        if not membership:
            return 0
        return ConversationMemberSerializer().get_unread_count(membership)


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    sender_email = serializers.CharField(source="sender.email", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id", "conversation", "sender", "sender_name", "sender_email",
            "body", "attachment_url", "created_at", "edited_at", "deleted_at",
        )
        read_only_fields = (
            "id", "conversation", "sender", "sender_name", "sender_email",
            "created_at", "edited_at", "deleted_at",
        )

    def validate(self, attrs):
        if not attrs.get("body") and not attrs.get("attachment_url"):
            raise serializers.ValidationError("A message needs text or an attachment.")
        return attrs