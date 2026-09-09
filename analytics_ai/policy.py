from core.classification_policy import ClassificationPolicy
from core.anonymity import AnonymousSourcePolicy
class AIClassificationPolicy:
    @staticmethod
    def include(*,user,classification): return ClassificationPolicy.may_use_for_ai(user=user,classification=classification)
    @staticmethod
    def source_mapping(*,obj,data): return AnonymousSourcePolicy.redact_mapping(data) if getattr(obj,'is_anonymous',False) else data
