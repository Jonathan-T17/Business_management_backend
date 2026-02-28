from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from companies.models import Company

User = settings.AUTH_USER_MODEL


class Notification(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]