from rest_framework.permissions import BasePermission
from core.capabilities import Capabilities as C
from .access import FormAccess

class CanManageFormTemplates(BasePermission):
    def has_permission(self, request, view):
        capability = C.PUBLISH_FORM_TEMPLATES if view.action in {'publish','archive','destroy'} else C.MANAGE_FORM_TEMPLATES
        return FormAccess.has(request.user, capability)

class CanUseForms(BasePermission):
    def has_permission(self, request, view):
        user=request.user
        if request.method in {'GET', 'HEAD', 'OPTIONS'}:
            return FormAccess.can_submit(user) or any(FormAccess.has(user,c) for c in (C.MANAGE_FORM_TEMPLATES,C.PUBLISH_FORM_TEMPLATES,C.VIEW_FORM_SUBMISSIONS,C.REVIEW_SUBMISSIONS))
        return FormAccess.can_submit(user)
