from rest_framework import serializers
from .models import Task, TaskActivity


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


class TaskActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivity
        fields = [
            "id",
            "task",
            "user",
            "action",
            "timestamp",
        ]
        read_only_fields = ("user", "timestamp")