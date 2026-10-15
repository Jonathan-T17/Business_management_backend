from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from core.data_classification import DataClassification
from core.visibility import VisibilityService


class AttachmentAccessService:
    """Attachments never grant access; they inherit it from the parent object."""

    @classmethod
    def can_view(cls, *, user, attachment):
        if not getattr(user, "company_id", None):
            return False
        if attachment.company_id != user.company_id:
            return False
        parent = attachment.content_object
        return bool(parent and VisibilityService.can_view_attachment(user=user, attachment=attachment))

    @classmethod
    def can_attach(cls, *, user, parent):
        if not getattr(user, "company_id", None):
            return False
        if getattr(parent, "company_id", None) != user.company_id:
            return False
        if parent._meta.label_lower == 'forms_engine.formsubmission':
            from forms_engine.attachments import can_upload_files
            return can_upload_files(user, parent)
        if parent._meta.label_lower == 'requests_app.businessrequest':
            if parent.form_submission_id:
                return False  # Linked forms keep their own file disclosure policy.
            from requests_app.services import BusinessRequestLifecycleService
            definition = BusinessRequestLifecycleService.resolve_definition(parent)
            return (parent.requester_id == user.pk and parent.status in {'DRAFT', 'RETURNED'}
                    and bool(definition and definition.attachments_allowed))
        return VisibilityService.can_view_generic_object(user=user, obj=parent)


class DocumentAccessService:
    @classmethod
    def can_view_sensitive(cls, user):
        return CapabilityService.has(user, getattr(Capabilities, "VIEW_SENSITIVE_DOCUMENTS", "VIEW_SENSITIVE_DOCUMENTS"))

    @classmethod
    def can_download(cls, *, user, document):
        if not VisibilityService.documents_queryset(user=user, queryset=type(document).objects.filter(pk=document.pk)).exists():
            return False
        classification = getattr(document, "classification", DataClassification.NORMAL)
        category_sensitive = bool(getattr(getattr(document, "category", None), "sensitive", False))
        if category_sensitive or classification in DataClassification.SENSITIVE:
            return cls.can_view_sensitive(user)
        return True
