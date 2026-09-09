from dataclasses import dataclass
SENSITIVE_CLASSIFICATIONS={"FINANCIAL","HR_CONFIDENTIAL","COMPENSATION","PRECISE_LOCATION","SECURITY_SENSITIVE","MANAGEMENT_CONFIDENTIAL"}
AI_EXCLUDED_CLASSIFICATIONS={"HR_CONFIDENTIAL","COMPENSATION","PRECISE_LOCATION","SECURITY_SENSITIVE"}
SEARCH_EXCLUDED_CLASSIFICATIONS={"HR_CONFIDENTIAL","COMPENSATION","PRECISE_LOCATION","SECURITY_SENSITIVE"}
NOTIFICATION_PREVIEW_EXCLUDED_CLASSIFICATIONS={"HR_CONFIDENTIAL","COMPENSATION","PRECISE_LOCATION","SECURITY_SENSITIVE","MANAGEMENT_CONFIDENTIAL"}
@dataclass(frozen=True)
class SecondaryDataDecision:
    allowed: bool
    redact_content: bool=False
    require_reason: bool=False
class SecondaryDataPolicy:
    @staticmethod
    def classification_of(obj, default="NORMAL"):
        return getattr(obj,"classification",None) or getattr(obj,"sensitivity",None) or default
    @classmethod
    def may_search(cls,*,obj,user,has_sensitive_capability=False):
        c=cls.classification_of(obj)
        return not (c in SEARCH_EXCLUDED_CLASSIFICATIONS and not has_sensitive_capability)
    @classmethod
    def may_use_for_ai(cls,*,obj):
        return cls.classification_of(obj) not in AI_EXCLUDED_CLASSIFICATIONS
    @classmethod
    def notification_preview(cls,*,classification,safe_message):
        return "A protected item requires your attention." if classification in NOTIFICATION_PREVIEW_EXCLUDED_CLASSIFICATIONS else safe_message
    @classmethod
    def export_decision(cls,*,classification,has_sensitive_export_capability):
        if classification in SENSITIVE_CLASSIFICATIONS:
            return SecondaryDataDecision(has_sensitive_export_capability,not has_sensitive_export_capability,True)
        return SecondaryDataDecision(True)
