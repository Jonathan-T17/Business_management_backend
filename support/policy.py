from core.classification import normalize
DEFAULT_DENIED={'COMPENSATION','HR_CONFIDENTIAL','PRECISE_LOCATION','SECURITY_SENSITIVE'}
class SupportClassificationPolicy:
    @classmethod
    def scope_for(cls,classification): return f'VIEW_{normalize(classification).value}'
    @classmethod
    def may_access(cls,*,classification,active_support_session):
        c=normalize(classification)
        if c.value in DEFAULT_DENIED or not active_support_session:return False
        return cls.scope_for(c) in set(active_support_session.scopes or [])
