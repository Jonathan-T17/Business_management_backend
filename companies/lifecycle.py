"""Workspace archive transitions. Employee records and restrictions are preserved."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import UserRateThrottle

from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.roles import Roles
from security.services import create_audit_log, terminate_company_sessions
from .models import Company


class WorkspaceLifecycleThrottle(UserRateThrottle):
    scope = "workspace_lifecycle"
    rate = "5/min"

    def allow_request(self, request, view):
        return True if request.method in ("GET", "HEAD", "OPTIONS") else super().allow_request(request, view)


class WorkspaceLifecycleInput(serializers.Serializer):
    company_name = serializers.CharField(max_length=255, trim_whitespace=False)
    reason = serializers.CharField(max_length=1000)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class WorkspaceArchiveResult(serializers.Serializer):
    message = serializers.CharField()
    recovery_until = serializers.DateTimeField()


class WorkspaceAccessInput(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class WorkspaceAccessResult(serializers.Serializer):
    message = serializers.CharField()
    is_active = serializers.BooleanField()


@transaction.atomic
def set_platform_workspace_access(*, company, actor, active, reason, request=None):
    if not CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN):
        raise PermissionDenied("Platform owner authority is required.")
    company = Company.objects.select_for_update().get(pk=company.pk)
    from .models import WorkspacePurgeReceipt
    if company.archived_at or WorkspacePurgeReceipt.objects.filter(workspace_id=company.pk).exists():
        raise ValidationError("This workspace is archived or erased. Ordinary reactivation is unavailable.")
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    if company.is_active == active:
        raise ValidationError("This workspace is already active." if active else "This workspace is already suspended.")
    company.is_active = active
    company.save(update_fields=("is_active", "updated_at"))
    if not active:
        terminate_company_sessions(company, actor=actor, reason="ACCOUNT_STATE", note=reason, request=request)
        from security.models import SupportAccessSession
        SupportAccessSession.objects.filter(company=company, status__in=("PENDING", "ACTIVE")).update(
            status="ENDED", ended_at=timezone.now(), end_reason="Workspace suspended")
    create_audit_log(user=actor, company=company, request=request, obj=company,
        action="WORKSPACE_REACTIVATED" if active else "WORKSPACE_SUSPENDED", severity="CRITICAL",
        description=reason.strip())
    return company


def validate_confirmation(actor, company, values):
    if values["company_name"] != company.name:
        raise ValidationError({"company_name": "Enter the company name exactly as shown."})
    if not actor.check_password(values["password"]):
        raise ValidationError({"password": "Your password could not be verified."})


class WorkspaceLifecycleService:
    @staticmethod
    @transaction.atomic
    def archive(*, company, actor, values, request=None):
        company = Company.objects.select_for_update().get(pk=company.pk)
        platform_owner = CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN)
        if not platform_owner and not (
            actor.is_active and not actor.is_deleted and actor.role == Roles.ADMIN
            and actor.company_id == company.pk and company.is_active
        ):
            raise PermissionDenied("Only an active company administrator or platform owner can archive this workspace.")
        validate_confirmation(actor, company, values)
        if company.archived_at:
            raise ValidationError("This workspace is already archived.")
        company.active_before_archive = company.is_active
        company.archived_at = timezone.now()
        company.recovery_until = company.archived_at + timedelta(days=30)
        company.archived_by = actor
        company.archive_reason = values["reason"]
        company.is_active = False
        company.save(update_fields=("active_before_archive", "archived_at", "recovery_until", "archived_by", "archive_reason", "is_active", "updated_at"))
        terminate_company_sessions(company, actor=actor, reason="ACCOUNT_STATE", note="Workspace archived", request=request)
        from security.models import SupportAccessSession
        SupportAccessSession.objects.filter(company=company, status__in=("PENDING", "ACTIVE")).update(status="ENDED", ended_at=timezone.now(), end_reason="Workspace archived")
        create_audit_log(user=actor, company=company, obj=company, request=request,
                         action="WORKSPACE_ARCHIVED", severity="CRITICAL", description=values["reason"],
                         metadata={"recovery_until": company.recovery_until.isoformat()})
        return company

    @staticmethod
    @transaction.atomic
    def restore(*, company, actor, values, request=None):
        if not CapabilityService.has(actor, Capabilities.PLATFORM_ADMIN):
            raise PermissionDenied("Only a platform owner can recover an archived workspace.")
        company = Company.objects.select_for_update().get(pk=company.pk)
        validate_confirmation(actor, company, values)
        from .models import WorkspacePurgeReceipt
        if WorkspacePurgeReceipt.objects.filter(workspace_id=company.pk).exists():
            raise ValidationError("The deletion ledger blocks recovery of this workspace.")
        if not company.archived_at:
            raise ValidationError("This workspace is not archived.")
        if not company.recovery_until or timezone.now() >= company.recovery_until:
            raise ValidationError("The recovery period has ended. Recovery is unavailable.")
        previous_archive = company.archived_at.isoformat()
        company.is_active = company.active_before_archive
        company.archived_at = None
        company.recovery_until = None
        company.archived_by = None
        company.archive_reason = ""
        company.save(update_fields=("is_active", "archived_at", "recovery_until", "archived_by", "archive_reason", "updated_at"))
        create_audit_log(user=actor, company=company, obj=company, request=request,
                         action="WORKSPACE_RESTORED", severity="CRITICAL", description=values["reason"],
                         metadata={"archived_at": previous_archive, "is_active": company.is_active})
        return company
