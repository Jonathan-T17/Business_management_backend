from dataclasses import dataclass
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
@dataclass(frozen=True)
class Entitlement:
    code:str
    enabled:bool
    limit:int|None=None
    used:int|None=None
class EntitlementService:
    FEATURES={"REPORTING","ADVANCED_ANALYTICS","FIELD_OPERATIONS","ADVANCED_WORKFLOWS","OFFICIAL_RECORDS","CUSTOM_FORMS","DATA_IMPORT","DATA_EXPORT","CHAT","AI_INSIGHTS"}
    @classmethod
    def subscription_for(cls,company):
        if company is None:return None
        return company.subscriptions.select_related("plan").filter(is_active=True).order_by("-started_at").first()
    @classmethod
    def is_subscription_valid(cls,company):
        s=cls.subscription_for(company)
        if not s:return False
        e=getattr(s,"expires_at",None)
        return not e or e>timezone.now()
    @classmethod
    def has_feature(cls,company,code):
        if code not in cls.FEATURES:return False
        s=cls.subscription_for(company)
        if not s or not cls.is_subscription_valid(company):return False
        mapping={"REPORTING":"reports_enabled","ADVANCED_ANALYTICS":"ai_analytics_enabled","FIELD_OPERATIONS":"field_operations_enabled","ADVANCED_WORKFLOWS":"advanced_workflows_enabled","OFFICIAL_RECORDS":"official_records_enabled","CUSTOM_FORMS":"custom_forms_enabled","DATA_IMPORT":"data_import_enabled","DATA_EXPORT":"data_export_enabled","CHAT":"chat_enabled","AI_INSIGHTS":"ai_analytics_enabled"}
        f=mapping.get(code)
        return bool(f and getattr(s.plan,f,False))
    @classmethod
    def require_feature(cls,company,code):
        if not cls.has_feature(company,code): raise PermissionDenied(f"{code.replace('_',' ').title()} is not included in this subscription.")
    @classmethod
    def limit(cls,company,resource):
        s=cls.subscription_for(company)
        if not s:return 0
        f={"USERS":"max_users","PROJECTS":"max_projects","BRANCHES":"max_branches","STORAGE_BYTES":"storage_limit_bytes"}.get(resource)
        return getattr(s.plan,f,None) if f else None
    @classmethod
    def require_capacity(cls,*,company,resource,used,delta=1):
        limit=cls.limit(company,resource)
        if limit in (None,-1):return
        if used+delta>limit:raise PermissionDenied(f"{resource.replace('_',' ').title()} subscription limit reached.")
