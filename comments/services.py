from activity.models import ActivityLog
from notifications.services import create_notification

from .models import Comment


def create_comment(
    *,
    user,
    project,
    task=None,
    content,
):
    comment = Comment.objects.create(
        company=project.company,
        project=project,
        task=task,
        user=user,
        content=content,
    )

    ActivityLog.objects.create(
        company=comment.company,
        project=comment.project,
        task=comment.task,
        user=user,
        action="COMMENT_ADDED",
        metadata={
            "comment_id": str(comment.id),
            "length": len(comment.content),
        },
    )

    memberships = (
        project.memberships
        .select_related("user")
        .exclude(user=user)
    )

    for membership in memberships:
        recipient = membership.user

        create_notification(
            recipient=recipient,
            company=comment.company,
            branch=getattr(recipient, "branch", None),
            notification_type="COMMENT_ADDED",
            title="New Comment",
            message=(
                f"{user.get_full_name() or user.email} "
                f"commented on project '{project.name}'."
            ),
            reference_id=str(comment.id),
        )

    return comment