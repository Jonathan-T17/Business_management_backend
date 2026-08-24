from django.db import models
from django.utils import timezone

from companies.models import Company


class Plan(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
    )

    max_users = models.PositiveIntegerField()
    max_projects = models.PositiveIntegerField()

    ai_analytics_enabled = models.BooleanField(
        default=False
    )

    reports_enabled = models.BooleanField(
        default=True
    )

    price_monthly = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["price_monthly", "name"]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    is_active = models.BooleanField(
        default=True
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-started_at"]

    @property
    def is_valid(self):
        """
        A subscription is valid only when it is active,
        its plan is active, and it has not expired.
        """
        if not self.is_active:
            return False

        if not self.plan.is_active:
            return False

        if self.expires_at and self.expires_at <= timezone.now():
            return False

        return True

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"
    