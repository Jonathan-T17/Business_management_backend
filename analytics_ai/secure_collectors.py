from core.secondary_policy import SecondaryDataPolicy
from subscriptions.entitlements import EntitlementService
class SecureAnalyticsCollector:
    @classmethod
    def require_analytics(cls,user):
        if not getattr(user,"company_id",None):return False
        EntitlementService.require_feature(user.company,"ADVANCED_ANALYTICS");return True
    @classmethod
    def safe_dynamic_fields(cls,fields):return [f for f in fields if SecondaryDataPolicy.may_use_for_ai(obj=f)]
class AIContextBuilder:
    @staticmethod
    def build(*,sources):return [s for s in sources if SecondaryDataPolicy.may_use_for_ai(obj=s)]
