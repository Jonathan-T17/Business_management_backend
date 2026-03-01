from django.utils import timezone
import uuid

from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from companies.models import Branch, Company
from projects.models import Project
from tasks.models import Task

User = settings.AUTH_USER_MODEL


class Report(models.Model):
    REPORT_TYPE_CHOICES = (
        ('GENERAL', 'General'),
        ('PROGRESS', 'Progress'),
        ('INCIDENT', 'Incident'),
        ('FEEDBACK', 'Feedback'),
        ('TASK', 'Task'),
        ('REQUEST', 'Request'),
        ('CUSTOM', 'Custom'),
    )

    VISIBILITY_CHOICES = (
        ('PRIVATE', 'Private'),
        ('COMPANY', 'Company'),
        ('PROJECT', 'Project'),
        ('BRANCH', 'Branch'),
    )

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False)

    title = models.CharField(max_length=255)
    description = models.TextField()

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='GENERAL'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports'
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports'
    )

    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='COMPANY'
    )

    is_anonymous = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    




class ReportField(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='fields'
    )

    key = models.CharField(max_length=100)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}: {self.value}"
    



class ReportComment(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='comments'
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='report_comments'
    )

    comment = models.TextField()

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Comment by {self.author.email}"