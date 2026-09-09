from dataclasses import dataclass
from core.capability_service import CapabilityService
from .classification import DataClassification,DisclosureMode,RULES,normalize,max_classification
@dataclass(frozen=True)
class DisclosureDecision:
    classification:DataClassification; mode:DisclosureMode; capability:str|None; reason_required:bool=False
class ClassificationPolicy:
    @classmethod
    def object_classification(cls,obj):
        direct=getattr(obj,'classification',None) or getattr(obj,'sensitivity',None); category=getattr(obj,'category',None); c=getattr(category,'classification',None)
        if category and getattr(category,'sensitive',False) and not c:c=DataClassification.MANAGEMENT_CONFIDENTIAL
        return max_classification(direct,c)
    @classmethod
    def can_disclose(cls,*,user,classification,owner_id=None):
        classification=normalize(classification); rule=RULES[classification]
        if classification==DataClassification.PERSONAL and owner_id==getattr(user,'id',None): return True
        return True if rule.capability is None else CapabilityService.has(user,rule.capability)
    @classmethod
    def decision(cls,*,user,classification,owner_id=None,hide_when_denied=True):
        classification=normalize(classification); rule=RULES[classification]
        if cls.can_disclose(user=user,classification=classification,owner_id=owner_id): return DisclosureDecision(classification,DisclosureMode.FULL,rule.capability,rule.export_requires_reason)
        return DisclosureDecision(classification,DisclosureMode.HIDDEN if hide_when_denied else DisclosureMode.REDACTED,rule.capability,rule.export_requires_reason)
    @classmethod
    def may_search(cls,*,user,classification):
        c=normalize(classification); return RULES[c].searchable and cls.can_disclose(user=user,classification=c)
    @classmethod
    def may_use_for_ai(cls,*,user,classification):
        c=normalize(classification); return RULES[c].ai_allowed and cls.can_disclose(user=user,classification=c)
    @classmethod
    def notification_text(cls,*,classification,safe_text):
        c=normalize(classification); return safe_text if RULES[c].notification_preview else 'A protected item requires your attention.'
