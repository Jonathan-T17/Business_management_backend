from rest_framework.exceptions import PermissionDenied,ValidationError
class ChatAccessService:
    @staticmethod
    def visible_conversations(*,user,queryset):
        if not getattr(user,"company_id",None):return queryset.none()
        return queryset.filter(company_id=user.company_id,memberships__user=user).distinct()
    @staticmethod
    def can_manage_members(*,user,conversation):
        membership=conversation.memberships.filter(user=user).first()
        return bool(membership and (conversation.created_by_id==user.id or getattr(membership,"can_manage_members",False)))
    @classmethod
    def require_manage_members(cls,*,user,conversation):
        if not cls.can_manage_members(user=user,conversation=conversation):raise PermissionDenied("You cannot manage this conversation's members.")
    @staticmethod
    def validate_scope_member(*,conversation,member):
        if member.company_id!=conversation.company_id or not member.is_active:raise ValidationError("Member must be an active user in this company.")
        if conversation.scope=="PROJECT" and not conversation.project.memberships.filter(user=member).exists():raise ValidationError("Member must belong to the project.")
        if conversation.scope=="BRANCH" and member.branch_id!=conversation.branch_id:raise ValidationError("Member must belong to the conversation branch.")
        p=getattr(member,"employee_profile",None)
        if conversation.scope=="DEPARTMENT" and getattr(p,"department_id",None)!=conversation.department_id:raise ValidationError("Member must belong to the conversation department.")
        if conversation.scope=="TEAM" and getattr(p,"team_id",None)!=conversation.team_id:raise ValidationError("Member must belong to the conversation team.")
