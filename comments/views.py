from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Comment
from .serializers import CommentSerializer
from activity.models import ActivityLog


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        comment = serializer.save(
            company=self.request.user.company,
            user=self.request.user
        )

        ActivityLog.objects.create(
            company=comment.company,
            project=comment.project,
            task=comment.task,
            user=self.request.user,
            action="COMMENT_ADDED",
            metadata={"length": len(comment.content)}
        )