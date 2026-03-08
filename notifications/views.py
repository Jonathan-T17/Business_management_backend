from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return notifications for the authenticated user
        return Notification.objects.filter(
            recipient=self.request.user,
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        # Ensure notifications are always tied to the current user + company
        serializer.save(
            recipient=self.request.user,
            company=self.request.user.company
        )

    @action(detail=False, methods=["get"])
    def unread(self, request):
        """Custom endpoint to fetch unread notifications"""
        unread = Notification.objects.filter(
            recipient=request.user,
            company=request.user.company,
            is_read=False
        )
        serializer = self.get_serializer(unread, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Custom endpoint to mark a single notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"status": "notification marked as read"})
    


    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):

        notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )

        notifications.update(is_read=True)

        return Response({"status": "all notifications marked as read"})