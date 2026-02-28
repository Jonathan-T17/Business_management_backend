from django.db import models

# Create your models here.
from django.db import models
from companies.models import Company


class Plan(models.Model):

    name = models.CharField(max_length=50, unique=True)

    max_users = models.PositiveIntegerField()
    max_projects = models.PositiveIntegerField()

    ai_analytics_enabled = models.BooleanField(default=False)
    reports_enabled = models.BooleanField(default=True)

    price_monthly = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.name


class Subscription(models.Model):

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT
    )

    is_active = models.BooleanField(default=True)

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)