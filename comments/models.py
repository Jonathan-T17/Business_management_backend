from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from companies.models import Company
from projects.models import Project
from tasks.models import Task

User = settings.AUTH_USER_MODEL


class Comment(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]