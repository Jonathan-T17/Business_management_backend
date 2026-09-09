from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from security.services import create_audit_log


class FieldOperationService:
    @staticmethod
    def _can_manage(user):
        return CapabilityService.has(user, getattr(Capabilities, "MANAGE_FIELD_OPERATIONS", "MANAGE_FIELD_OPERATIONS"))

    @staticmethod
    def _is_worker(user, activity):
        return getattr(activity, "employee_id", None) == user.id

    @classmethod
    def _assert_actor(cls, *, user, activity):
        if not (cls._is_worker(user, activity) or cls._can_manage(user)):
            raise PermissionDenied("Field activity access denied.")

    @classmethod
    @transaction.atomic
    def start_activity(cls, *, activity, user, request=None):
        activity = type(activity).objects.select_for_update().get(pk=activity.pk)
        cls._assert_actor(user=user, activity=activity)
        if activity.status not in ("PLANNED", "ASSIGNED"):
            raise ValidationError("Activity cannot be started in its current state.")
        activity.status = "IN_PROGRESS"
        if hasattr(activity, "started_at"):
            activity.started_at = timezone.now()
            activity.save(update_fields=["status", "started_at", "updated_at"])
        else:
            activity.save(update_fields=["status", "updated_at"])
        create_audit_log(user=user, company=activity.company, request=request, action="UPDATE", description="Field activity started.", obj=activity)
        return activity

    @classmethod
    @transaction.atomic
    def arrive_stop(cls, *, stop, user, latitude=None, longitude=None, request=None):
        stop = type(stop).objects.select_for_update().select_related("activity").get(pk=stop.pk)
        cls._assert_actor(user=user, activity=stop.activity)
        if stop.status != "PENDING":
            raise ValidationError("Only a pending stop can be marked arrived.")
        stop.status = "ARRIVED"
        stop.arrived_at = timezone.now()
        if latitude is not None and longitude is not None:
            stop.latitude = latitude
            stop.longitude = longitude
        stop.save(update_fields=["status", "arrived_at", "latitude", "longitude"])
        # Deliberately do NOT run stop-completion requirements here.
        create_audit_log(user=user, company=stop.activity.company, request=request, action="UPDATE", description="Field stop arrival recorded.", obj=stop)
        return stop

    @classmethod
    @transaction.atomic
    def complete_stop(cls, *, stop, user, validator=None, request=None):
        stop = type(stop).objects.select_for_update().select_related("activity").get(pk=stop.pk)
        cls._assert_actor(user=user, activity=stop.activity)
        if stop.status not in ("PENDING", "ARRIVED"):
            raise ValidationError("Stop cannot be completed in its current state.")
        if validator:
            validator(stop)
        stop.status = "COMPLETED"
        stop.completed_at = timezone.now()
        stop.save(update_fields=["status", "completed_at"])
        create_audit_log(user=user, company=stop.activity.company, request=request, action="UPDATE", description="Field stop completed.", obj=stop)
        return stop

    @classmethod
    @transaction.atomic
    def complete_activity(cls, *, activity, user, validator=None, request=None):
        activity = type(activity).objects.select_for_update().get(pk=activity.pk)
        cls._assert_actor(user=user, activity=activity)
        if activity.status != "IN_PROGRESS":
            raise ValidationError("Only an in-progress activity can be completed.")
        if validator:
            validator(activity)
        incomplete = activity.stops.exclude(status__in=["COMPLETED", "SKIPPED"]).exists()
        if incomplete:
            raise ValidationError("Complete or skip all field stops first.")
        activity.status = "COMPLETED"
        if hasattr(activity, "completed_at"):
            activity.completed_at = timezone.now()
            activity.save(update_fields=["status", "completed_at", "updated_at"])
        else:
            activity.save(update_fields=["status", "updated_at"])
        create_audit_log(user=user, company=activity.company, request=request, action="UPDATE", description="Field activity completed.", obj=activity)
        return activity
