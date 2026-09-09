FORBIDDEN_METADATA_KEYS={"latitude","longitude","password","token","otp","secret","base_salary","salary","compensation","private_message_body"}
class ActivityMetadataSanitizer:
    @classmethod
    def sanitize(cls,metadata):return {k:v for k,v in (metadata or {}).items() if k.lower() not in FORBIDDEN_METADATA_KEYS}
class ActivityFeedService:
    @classmethod
    def visible_queryset(cls,*,user,queryset,visibility_service):
        if not getattr(user,"company_id",None):return queryset.none()
        queryset=queryset.filter(company_id=user.company_id);allowed=[]
        for item in queryset.select_related("project","task"):
            if item.task and visibility_service.can_view_generic_object(user=user,obj=item.task):allowed.append(item.pk)
            elif item.project and visibility_service.can_view_generic_object(user=user,obj=item.project):allowed.append(item.pk)
            elif item.user_id==user.id:allowed.append(item.pk)
        return queryset.filter(pk__in=allowed)
