from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from security.services import create_audit_log
from .access import AttachmentAccessService, DocumentAccessService


class DocumentLifecycleService:
    @classmethod
    @transaction.atomic
    def add_version(cls, *, document, file, original_filename, mime_type, file_size, actor, change_note="", request=None):
        if not DocumentAccessService.can_download(user=actor, document=document):
            raise PermissionDenied("Document access denied.")
        document = type(document).objects.select_for_update().get(pk=document.pk)
        if document.status == "ARCHIVED":
            raise ValidationError("Archived documents cannot receive new versions.")
        next_version = document.current_version + 1 if document.versions.exists() else 1
        version = document.versions.create(
            version_number=next_version,
            file=file,
            original_filename=original_filename,
            mime_type=mime_type or "",
            file_size=file_size or 0,
            change_note=change_note or "",
            uploaded_by=actor,
        )
        document.current_version = next_version
        document.save(update_fields=["current_version", "updated_at"])
        create_audit_log(user=actor, company=document.company, request=request, action="UPDATE", description=f"Document version {next_version} added.", obj=document)
        return version

    @classmethod
    @transaction.atomic
    def archive(cls, *, document, actor, reason, request=None):
        reason = (reason or "").strip()
        if not reason:
            raise ValidationError("A reason is required.")
        document = type(document).objects.select_for_update().get(pk=document.pk)
        document.status = "ARCHIVED"
        document.is_active = False
        document.save(update_fields=["status", "is_active", "updated_at"])
        create_audit_log(user=actor, company=document.company, request=request, action="UPDATE", description="Document archived.", obj=document, metadata={"reason": reason})
        return document


class AttachmentService:
    @classmethod
    @transaction.atomic
    def create(cls, *, actor, parent, file, original_filename, mime_type, file_size, attachment_type="FILE", description=""):
        if not AttachmentAccessService.can_attach(user=actor, parent=parent):
            raise PermissionDenied("You cannot attach files to this object.")
        from django.contrib.contenttypes.models import ContentType
        from .models import Attachment
        return Attachment.objects.create(
            company=parent.company,
            uploaded_by=actor,
            content_type=ContentType.objects.get_for_model(parent, for_concrete_model=False),
            object_id=str(parent.pk),
            file=file,
            original_filename=original_filename,
            mime_type=mime_type or "",
            file_size=file_size or 0,
            attachment_type=attachment_type,
            description=description or "",
        )
