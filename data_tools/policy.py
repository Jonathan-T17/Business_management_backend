from rest_framework.exceptions import PermissionDenied,ValidationError
from core.classification import RULES,normalize
from core.classification_policy import ClassificationPolicy
class SensitiveExportPolicy:
    @classmethod
    def require(cls,*,user,classification,purpose):
        c=normalize(classification); rule=RULES[c]
        if rule.capability and not ClassificationPolicy.can_disclose(user=user,classification=c): raise PermissionDenied('You cannot export this protected data.')
        if rule.export_requires_reason and not (purpose or '').strip(): raise ValidationError('A business purpose is required for this export.')
        return True
class SearchClassificationPolicy:
    @staticmethod
    def include(*,user,classification): return ClassificationPolicy.may_search(user=user,classification=classification)
