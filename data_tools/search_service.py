from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from core.secondary_policy import SecondaryDataPolicy
class SecureGlobalSearchService:
    @classmethod
    def search(cls,*,user,query,registry,limit=10):
        if not CapabilityService.has(user,Capabilities.GLOBAL_SEARCH) or not getattr(user,"company_id",None):return []
        results=[]
        for adapter in registry:
            qs=adapter.visible_queryset(user=user)
            for obj in adapter.search(queryset=qs,query=query)[:limit]:
                if not SecondaryDataPolicy.may_search(obj=obj,user=user,has_sensitive_capability=adapter.can_search_sensitive(user=user,obj=obj)):continue
                results.append(adapter.to_result(obj=obj,user=user))
                if len(results)>=100:return results
        return results
