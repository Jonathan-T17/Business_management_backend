from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.access import ProjectAccess
from tasks.access import TaskAccess
from security.services import create_audit_log
from .models import Comment

class CommentService:
    @classmethod
    @transaction.atomic
    def create(cls, *, user, project, content, task=None, request=None):
        if not ProjectAccess.can_view(user, project): raise ValidationError('You cannot comment on this project.')
        if task and (task.project_id != project.id or not TaskAccess.can_view(user, task)):
            raise ValidationError({'task':'Task is not available in this project.'})
        if not (content or '').strip(): raise ValidationError({'content':'Comment cannot be empty.'})
        comment=Comment.objects.create(company=project.company,project=project,task=task,user=user,content=content.strip())
        create_audit_log(user=user,company=project.company,request=request,action='CREATE',description='Comment added.',obj=comment)
        return comment

    @classmethod
    @transaction.atomic
    def edit(cls, *, comment, actor, content, request=None):
        comment=Comment.objects.select_for_update().get(pk=comment.pk)
        if comment.user_id != actor.id: raise ValidationError('You can only edit your own comment.')
        if not ProjectAccess.can_view(actor, comment.project): raise ValidationError('Comment is not accessible.')
        if getattr(comment,'is_deleted',False): raise ValidationError('Deleted comments cannot be edited.')
        comment.content=(content or '').strip()
        if not comment.content: raise ValidationError({'content':'Comment cannot be empty.'})
        if hasattr(comment,'edited_at'): comment.edited_at=timezone.now(); fields=['content','edited_at','updated_at']
        else: fields=['content','updated_at']
        comment.save(update_fields=fields)
        create_audit_log(user=actor,company=comment.company,request=request,action='UPDATE',description='Comment edited.',obj=comment)
        return comment

    @classmethod
    @transaction.atomic
    def soft_delete(cls, *, comment, actor, can_moderate=False, request=None):
        comment=Comment.objects.select_for_update().get(pk=comment.pk)
        if comment.user_id != actor.id and not can_moderate: raise ValidationError('You cannot delete this comment.')
        if hasattr(comment,'is_deleted'):
            comment.is_deleted=True; comment.deleted_at=timezone.now(); comment.deleted_by=actor
            comment.save(update_fields=['is_deleted','deleted_at','deleted_by','updated_at'])
        else:
            raise ValidationError('Comment model requires Phase 4 soft-delete migration before deletion can be enabled.')
        create_audit_log(user=actor,company=comment.company,request=request,action='DELETE',description='Comment removed.',obj=comment)
        return comment
