from rest_framework import serializers
from .models import SupportMessage, SupportTicket

class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    class Meta:
        model = SupportMessage
        fields = ("id","author_name","body","visibility","created_at")
        read_only_fields = fields

class SupportTicketListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True)
    class Meta:
        model = SupportTicket
        fields = ("id","reference","category","sensitivity","subject","priority","requested_priority","status","created_by_name","assigned_to_name","created_at","updated_at")
        read_only_fields = fields

class SupportTicketDetailSerializer(SupportTicketListSerializer):
    messages = serializers.SerializerMethodField()
    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + ("description","context","messages","resolved_at","closed_at")
    def get_messages(self, obj):
        request = self.context.get("request")
        qs = obj.messages.all()
        if request and not getattr(request.user, "is_superuser", False):
            from core.capabilities import Capabilities
            from core.capability_service import CapabilityService
            if not CapabilityService.has(request.user, Capabilities.PLATFORM_SUPPORT):
                qs = qs.filter(visibility="CUSTOMER")
        return SupportMessageSerializer(qs, many=True).data

class SupportTicketCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=SupportTicket.CATEGORY_CHOICES)
    subject = serializers.CharField(max_length=255)
    description = serializers.CharField()
    requested_priority = serializers.ChoiceField(choices=SupportTicket.PRIORITY_CHOICES, default="NORMAL")
    context = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data):
        from .services import SupportTicketService
        request = self.context["request"]
        return SupportTicketService.create(actor=request.user, request=request, **validated_data)


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ("status", "priority", "assigned_to")

    def validate_assigned_to(self, value):
        from core.capabilities import Capabilities
        from core.capability_service import CapabilityService
        if value and not CapabilityService.has(value, Capabilities.PLATFORM_SUPPORT):
            raise serializers.ValidationError("Assignee must be a platform support user.")
        return value


SupportTicketSerializer = SupportTicketDetailSerializer
