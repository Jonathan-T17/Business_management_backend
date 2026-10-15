"""Filter before pagination so outstanding invitations do not hide in history."""
from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from organizations.models import EmployeeProfile


def filter_invitation_journey(queryset, bucket):
    if bucket not in {"active", "history"}:
        raise ValidationError({"bucket": "Choose active or history."})
    assigned = EmployeeProfile.objects.filter(
        company_id=OuterRef("company_id"), user__email__iexact=OuterRef("email"),
        status="ACTIVE", position__is_active=True, position__company_id=OuterRef("company_id"),
    )
    queryset = queryset.annotate(has_active_position=Exists(assigned))
    awaiting = Q(status="ACCEPTED", has_active_position=False) & ~Q(role="ADMIN")
    pending = Q(status="PENDING", expires_at__gt=timezone.now())
    active = awaiting | pending
    if bucket == "history":
        return queryset.exclude(active).order_by("-created_at", "-pk")
    return queryset.filter(active).annotate(
        journey_order=Case(When(awaiting, then=Value(0)), default=Value(1), output_field=IntegerField()),
    ).order_by("journey_order", "-created_at", "-pk")
