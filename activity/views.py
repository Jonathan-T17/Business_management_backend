from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ActivityLog
from .serializers import ActivityLogSerializer


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivityLog.objects.filter(
            company=self.request.user.company
        )