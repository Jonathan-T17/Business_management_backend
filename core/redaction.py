from copy import deepcopy
from .classification import DisclosureMode,normalize
from .classification_policy import ClassificationPolicy
REDACTED='[REDACTED]'
class FieldRedactionService:
    @classmethod
    def redact_mapping(cls,*,user,data,schema,owner_id=None):
        out=deepcopy(data or {})
        for key,c in (schema or {}).items():
            if key in out and ClassificationPolicy.decision(user=user,classification=c,owner_id=owner_id,hide_when_denied=False).mode!=DisclosureMode.FULL: out[key]=REDACTED
        return out
    @classmethod
    def filter_dynamic_fields(cls,*,user,fields,owner_id=None):
        result=[]
        for f in fields:
            c=normalize(f.get('classification') if isinstance(f,dict) else getattr(f,'classification','NORMAL'))
            if ClassificationPolicy.decision(user=user,classification=c,owner_id=owner_id).mode!=DisclosureMode.HIDDEN: result.append(f)
        return result
