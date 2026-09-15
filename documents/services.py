from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from security.services import create_audit_log
from .access import AttachmentAccessService, DocumentAccessService

MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024
MAX_DOCUMENT_SIZE = 25 * 1024 * 1024


def validate_uploaded_file(file, *, max_size):
    import mimetypes
    from pathlib import Path
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".txt", ".csv", ".docx", ".xlsx", ".pptx"}
    if not file or not 0 < file.size <= max_size:
        raise ValidationError({"file": "The file is empty or exceeds the upload limit."})
    if Path(file.name).suffix.lower() not in allowed:
        raise ValidationError({"file": "This file type is not supported."})
    return mimetypes.guess_type(file.name)[0] or "application/octet-stream"


def validate_attachment_target(*, content_type, object_id, user):
    from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
    try:
        parent = content_type.get_object_for_this_type(pk=object_id)
    except (ObjectDoesNotExist, DjangoValidationError, ValueError, TypeError):
        raise ValidationError("Attachment target is unavailable.")
    if not AttachmentAccessService.can_attach(user=user, parent=parent):
        raise PermissionDenied("Attachment target is unavailable.")
    return parent, parent.company


class DocumentService:
    @staticmethod
    def add_version(*, document, file, user, change_note="", request=None):
        mime_type = validate_uploaded_file(file, max_size=MAX_DOCUMENT_SIZE)
        return DocumentLifecycleService.add_version(document=document, file=file, actor=user,
            original_filename=file.name, mime_type=mime_type, file_size=file.size,
            change_note=change_note, request=request)


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
        parent = type(parent).objects.select_for_update().get(pk=parent.pk)
        if not AttachmentAccessService.can_attach(user=actor, parent=parent):
            raise PermissionDenied("You cannot attach files to this object.")
        from subscriptions.services import SubscriptionService
        type(parent.company).objects.select_for_update().get(pk=parent.company_id)
        mime_type = validate_uploaded_file(file, max_size=MAX_ATTACHMENT_SIZE)
        if not SubscriptionService.can_upload(parent.company, additional_bytes=file.size):
            raise ValidationError({'file': 'Your subscription storage limit has been reached.'})
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
