from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "created_by",
            "assignees",
            "status",
            "due_date",
            "created_at",
        ]
        read_only_fields = ("created_by",)