from core.classification_policy import ClassificationPolicy
class RequestDisclosurePolicy:
    @classmethod
    def requester_visible(cls,*,request_obj,user):
        c=getattr(getattr(request_obj,'request_type_definition',None),'classification','NORMAL')
        if c in {'HR_CONFIDENTIAL','COMPENSATION'}: return ClassificationPolicy.can_disclose(user=user,classification=c,owner_id=getattr(request_obj,'requester_id',None))
        return True
