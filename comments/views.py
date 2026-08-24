from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.audit import ActivityAudit
from core.tenant import TenantService
from security.viewsets import SecureModelViewSet

from .models import Comment
from .serializers import CommentSerializer
from .permissions import IsCommentParticipant
from .services import create_comment


class CommentViewSet(SecureModelViewSet):
    """
    Manage project and task comments.

    Security model:
    - authenticated users only
    - company/tenant isolation
    - project membership protection
    - task must belong to selected project
    - audit logging
    - project-member notifications
    """

    queryset = Comment.objects.select_related(
        "company",
        "project",
        "task",
        "user",
    )

    serializer_class = CommentSerializer

    permission_classes = [
        IsAuthenticated,
        IsCommentParticipant,
    ]

    audit_action = "COMMENT"

    # ------------------------------------------------------
    # Queryset
    # ------------------------------------------------------

    def get_queryset(self):
        user = self.request.user

        queryset = self.queryset.filter(
            company=user.company
        )

        # Superuser/admin can see comments across their company.
        if getattr(user, "role", None) in (
            "SUPERUSER",
            "ADMIN",
        ):
            return queryset

        # Ordinary users can only see comments belonging
        # to projects they are members of.
        return queryset.filter(
            project__memberships__user=user
        ).distinct()

    # ------------------------------------------------------
    # Create
    # ------------------------------------------------------

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        task = serializer.validated_data.get("task")
        content = serializer.validated_data["content"]

        comment = create_comment(
            user=self.request.user,
            project=project,
            task=task,
            content=content,
        )

        # SecureModelViewSet audit
        ActivityAudit.log(
            user=self.request.user,
            company=comment.company,
            project=comment.project,
            task=comment.task,
            action="COMMENT_ADDED",
            metadata={
                "object_type": "Comment",
                "object_id": str(comment.id),
                "content_length": len(comment.content),
            },
        )

        # Store the created object so DRF can return it.
        self._created_comment = comment

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------

    def perform_update(self, serializer):
        comment = self.get_object()

        # Only the comment author or administrator should
        # modify a comment.
        if (
            comment.user_id != self.request.user.id
            and getattr(self.request.user, "role", None)
            not in ("SUPERUSER", "ADMIN")
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You can only edit your own comments."
            )

        comment = serializer.save()

        ActivityAudit.log(
            user=self.request.user,
            company=comment.company,
            project=comment.project,
            task=comment.task,
            action="COMMENT_UPDATED",
            metadata={
                "object_type": "Comment",
                "object_id": str(comment.id),
            },
        )

    # ------------------------------------------------------
    # Delete
    # ------------------------------------------------------

    def perform_destroy(self, instance):
        # Only author/admin/superuser may delete.
        if (
            instance.user_id != self.request.user.id
            and getattr(self.request.user, "role", None)
            not in ("SUPERUSER", "ADMIN")
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You can only delete your own comments."
            )

        ActivityAudit.log(
            user=self.request.user,
            company=instance.company,
            project=instance.project,
            task=instance.task,
            action="COMMENT_DELETED",
            metadata={
                "object_type": "Comment",
                "object_id": str(instance.id),
            },
        )

        instance.delete()

    # ------------------------------------------------------
    # Project comments
    # ------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="project/(?P<project_id>[^/.]+)",
    )
    def project_comments(self, request, project_id=None):
        comments = self.get_queryset().filter(
            project_id=project_id
        )

        serializer = self.get_serializer(
            comments,
            many=True,
        )

        return Response(serializer.data)

    # ------------------------------------------------------
    # Task comments
    # ------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="task/(?P<task_id>[^/.]+)",
    )
    def task_comments(self, request, task_id=None):
        comments = self.get_queryset().filter(
            task_id=task_id
        )

        serializer = self.get_serializer(
            comments,
            many=True,
        )

        return Response(serializer.data)