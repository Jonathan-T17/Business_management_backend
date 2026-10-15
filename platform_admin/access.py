from django.db import transaction
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from drf_spectacular.utils import extend_schema
from users.models import User
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService
from security.services import terminate_user_sessions, create_audit_log
from .permissions import IsPlatformSuperUser
from .maintenance import MaintenanceWriteThrottle


class OperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name", "email", "platform_duty")
        read_only_fields = fields


class DutyChange(serializers.Serializer):
    user_id = serializers.UUIDField()
    duty = serializers.ChoiceField(choices=("OWNER", "SECURITY", "SUPPORT", "SUBSCRIPTIONS", "AUDITOR"))
    expected_duty = serializers.CharField(max_length=20)
    reason = serializers.CharField(max_length=1000)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class PlatformAccessView(APIView):
    permission_classes = (IsPlatformSuperUser,)
    throttle_classes = (MaintenanceWriteThrottle,)

    @extend_schema(responses=OperatorSerializer(many=True))
    def get(self, request):
        users = User.objects.filter(is_superuser=True, is_staff=True, is_active=True, is_deleted=False).order_by("full_name", "pk")
        return Response(OperatorSerializer(users, many=True).data)

    @extend_schema(request=DutyChange, responses=OperatorSerializer)
    @transaction.atomic
    def post(self, request):
        data = DutyChange(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        list(User.objects.select_for_update().filter(is_superuser=True, platform_duty="OWNER").order_by("pk"))
        actor = User.objects.get(pk=request.user.pk)
        if not CapabilityService.has(actor, C.PLATFORM_ADMIN):
            raise PermissionDenied("Platform owner authority is required.")
        if not actor.check_password(values["password"]):
            raise ValidationError({"password": "Your password could not be verified."})
        target = User.objects.select_for_update().filter(pk=values["user_id"], is_superuser=True, is_staff=True, is_active=True, is_deleted=False).first()
        if target is None:
            raise ValidationError("Choose an active platform operator.")
        if target.platform_duty != values["expected_duty"]:
            raise ValidationError("This assignment changed. Refresh before saving.")
        if target.platform_duty == values["duty"]:
            raise ValidationError("Choose a different duty.")
        if target.platform_duty == "OWNER" and values["duty"] != "OWNER" and not User.objects.filter(
                is_superuser=True, is_staff=True, is_active=True, is_deleted=False, must_change_password=False, platform_duty="OWNER").exclude(pk=target.pk).exists():
            raise ValidationError("Keep at least one active platform owner.")
        previous = target.platform_duty
        target.platform_duty = values["duty"]
        target.save(update_fields=("platform_duty",))
        terminate_user_sessions(target, actor=actor, reason="SECURITY", note="Platform duty changed", request=request)
        create_audit_log(user=actor, request=request, action="PLATFORM_DUTY_CHANGED", severity="CRITICAL", obj=target,
                         description=values["reason"], metadata={"previous_duty": previous, "duty": target.platform_duty})
        return Response(OperatorSerializer(target).data)
