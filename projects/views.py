from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Project, ProjectMembership
from .serializers import ProjectSerializer, ProjectMembershipSerializer
from .permissions import IsProjectMember, IsProjectOwnerOrManager


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            memberships__user=self.request.user,
            is_active=True
        ).distinct()

    def perform_create(self, serializer):
        project = serializer.save(
            company=self.request.user.company,
            created_by=self.request.user
        )

        ProjectMembership.objects.create(
            project=project,
            user=self.request.user,
            role="OWNER"
        )


class ProjectMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMembershipSerializer
    permission_classes = [IsAuthenticated, IsProjectOwnerOrManager]

    def get_queryset(self):
        return ProjectMembership.objects.filter(
            project__memberships__user=self.request.user
        )