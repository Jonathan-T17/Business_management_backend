from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from companies.models import Company, WorkspacePurgeReceipt
from companies.lifecycle import WorkspaceLifecycleInput, WorkspaceLifecycleThrottle, validate_confirmation
from companies.purge import preview_purge, purge_workspace, require_owner, resume_file_cleanup
from security.services import create_audit_log
from .permissions import IsPlatformSuperUser


class PurgePreviewSerializer(serializers.Serializer):
    fingerprint = serializers.CharField()
    eligible = serializers.BooleanField()
    blockers = serializers.ListField(child=serializers.CharField())
    recovery_until = serializers.DateTimeField(allow_null=True)
    hold_reason = serializers.CharField(allow_blank=True)
    records = serializers.DictField(child=serializers.IntegerField())
    files_count = serializers.IntegerField()
    accounts_to_detach = serializers.IntegerField()
    backup_retention_days = serializers.IntegerField()


class PurgeInput(WorkspaceLifecycleInput):
    fingerprint = serializers.CharField(min_length=64, max_length=64)
    acknowledge_backups = serializers.BooleanField()


class HoldInput(WorkspaceLifecycleInput):
    hold = serializers.BooleanField()


class ReceiptSerializer(serializers.ModelSerializer):
    files_remaining = serializers.SerializerMethodField()

    def get_files_remaining(self, obj) -> int:
        return len(obj.pending_files)

    class Meta:
        model = WorkspacePurgeReceipt
        fields = ("id", "workspace_id", "status", "created_at", "completed_at", "counts", "files_remaining", "failure_code")
        read_only_fields = fields


class WorkspaceDeletionViewSet(viewsets.GenericViewSet):
    queryset = Company.objects.all()
    permission_classes = (IsPlatformSuperUser,)
    throttle_classes = (WorkspaceLifecycleThrottle,)
    serializer_class = PurgePreviewSerializer

    @extend_schema(responses=PurgePreviewSerializer)
    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        company = get_object_or_404(Company, pk=pk)
        return Response(preview_purge(company=company, actor=request.user))

    @extend_schema(request=PurgeInput, responses=ReceiptSerializer)
    @action(detail=True, methods=["post"], url_path="purge")
    def purge(self, request, pk=None):
        data = PurgeInput(data=request.data)
        data.is_valid(raise_exception=True)
        company = get_object_or_404(Company, pk=pk)
        values = data.validated_data
        receipt = purge_workspace(company=company, actor=request.user, values=values,
            fingerprint=values["fingerprint"], acknowledge_backups=values["acknowledge_backups"], request=request)
        return Response(ReceiptSerializer(receipt).data)

    @extend_schema(request=HoldInput, responses=PurgePreviewSerializer)
    @action(detail=True, methods=["post"], url_path="hold")
    @transaction.atomic
    def hold(self, request, pk=None):
        require_owner(request.user)
        values = HoldInput(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        company = get_object_or_404(Company.objects.select_for_update(), pk=pk)
        validate_confirmation(request.user, company, data)
        company.deletion_hold_reason = data["reason"] if data["hold"] else ""
        company.save(update_fields=("deletion_hold_reason", "updated_at"))
        create_audit_log(user=request.user, company=company, request=request, obj=company,
            action="WORKSPACE_RETENTION_HOLD_CHANGED", severity="CRITICAL", description=data["reason"], metadata={"hold": data["hold"]})
        return Response(preview_purge(company=company, actor=request.user))


class RetryInput(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)
    reason = serializers.CharField(max_length=1000)


class WorkspacePurgeReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsPlatformSuperUser,)
    throttle_classes = (WorkspaceLifecycleThrottle,)
    serializer_class = ReceiptSerializer
    queryset = WorkspacePurgeReceipt.objects.all()

    @extend_schema(request=RetryInput, responses=ReceiptSerializer)
    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        # Only password and reason apply: the company no longer exists to name.
        from rest_framework.exceptions import ValidationError
        data = RetryInput(data=request.data)
        data.is_valid(raise_exception=True)
        if not request.user.check_password(data.validated_data["password"]):
            raise ValidationError({"password": "Your password could not be verified."})
        receipt = self.get_object()
        create_audit_log(user=request.user, request=request, action="WORKSPACE_PURGE_RETRY", severity="CRITICAL",
            description=data.validated_data["reason"], metadata={"receipt": str(receipt.pk)})
        return Response(ReceiptSerializer(resume_file_cleanup(receipt.pk, actor=request.user, request=request)).data)
