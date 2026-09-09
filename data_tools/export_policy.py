from rest_framework.exceptions import PermissionDenied,ValidationError
from core.secondary_policy import SecondaryDataPolicy
class ExportPolicyService:
    @classmethod
    def authorize(cls,*,user,obj,has_sensitive_export_capability,purpose=""):
        c=SecondaryDataPolicy.classification_of(obj)
        d=SecondaryDataPolicy.export_decision(classification=c,has_sensitive_export_capability=has_sensitive_export_capability)
        if not d.allowed:raise PermissionDenied("You cannot export this protected data.")
        if d.require_reason and not (purpose or "").strip():raise ValidationError("A business purpose is required for sensitive exports.")
        return d
