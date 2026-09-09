from core.classification_policy import ClassificationPolicy
class FieldLocationDisclosurePolicy:
    @classmethod
    def coordinates(cls,*,stop,user):
        if not ClassificationPolicy.can_disclose(user=user,classification='PRECISE_LOCATION'): return {'latitude':None,'longitude':None}
        return {'latitude':stop.latitude,'longitude':stop.longitude}
