class AnonymousSourcePolicy:
    AUTHOR_KEYS={'created_by','created_by_id','created_by_email','submitted_by','submitted_by_id','submitted_by_email','requester','requester_email','author','author_email','employee_id','user_id'}
    @classmethod
    def redact_mapping(cls,data): return {k:v for k,v in (data or {}).items() if k not in cls.AUTHOR_KEYS}
    @classmethod
    def display_identity(cls,*,obj,viewer): return None if getattr(obj,'is_anonymous',False) else getattr(obj,'created_by',None)
