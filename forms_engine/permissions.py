from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities as C
from .access import FormAccess

class CanManageFormTemplates(BasePermission):
    def has_permission(self, request, view):
        if view.action == 'choices':
            return any(FormAccess.has(request.user, capability) for capability in (C.MANAGE_FORM_TEMPLATES, C.PUBLISH_FORM_TEMPLATES))
        capability = C.PUBLISH_FORM_TEMPLATES if view.action in {'publish','archive','destroy'} else C.MANAGE_FORM_TEMPLATES
        return FormAccess.has(request.user, capability)

class CanUseForms(BasePermission):
    def has_permission(self, request, view):
        user=request.user
        if request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return FormAccess.can_submit(user) or any(FormAccess.has(user,c) for c in (C.MANAGE_FORM_TEMPLATES,C.PUBLISH_FORM_TEMPLATES,C.VIEW_FORM_SUBMISSIONS,C.REVIEW_SUBMISSIONS))
        return FormAccess.can_submit(user)


class CanUseFormSubmissions(CanUseForms):
    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return True
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            return False
        from core.visibility import VisibilityService
        from .models import FormSubmission
        # Object visibility still limits reads to the actual assigned records.
        return VisibilityService.workflow_object_ids(
            user=request.user, model=FormSubmission,
            delegated_permission=C.REVIEW_SUBMISSIONS,
        ).exists()
