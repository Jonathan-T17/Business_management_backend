from .redaction import FieldRedactionService
class ClassificationAwareSerializerMixin:
    classified_fields={}
    def to_representation(self,instance):
        data=super().to_representation(instance); request=self.context.get('request')
        if not request or not getattr(request.user,'is_authenticated',False): return data
        owner_id=getattr(instance,'owner_id',None) or getattr(instance,'user_id',None)
        return FieldRedactionService.redact_mapping(user=request.user,data=data,schema=self.classified_fields,owner_id=owner_id)
