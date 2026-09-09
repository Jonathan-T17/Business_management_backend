class AllowedActionsSerializerMixin:
    def actions_for(self,instance,user): return []
    def to_representation(self,instance):
        data=super().to_representation(instance); request=self.context.get('request')
        data['allowed_actions']=self.actions_for(instance,request.user) if request and request.user.is_authenticated else []
        return data
