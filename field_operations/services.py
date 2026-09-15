from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.capability_service import CapabilityService
from core.capabilities import Capabilities
from security.services import create_audit_log


class FieldOperationService:
    @staticmethod
    def _coordinates(latitude, longitude):
        from decimal import Decimal, InvalidOperation
        if latitude is None and longitude is None:
            return None
        try:
            lat, lon = Decimal(str(latitude)), Decimal(str(longitude))
            if not lat.is_finite() or not lon.is_finite() or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError("Provide a valid latitude and longitude together.")
        return lat, lon

    @staticmethod
    def _can_manage(user):
        return CapabilityService.has(user, getattr(Capabilities, "MANAGE_FIELD_OPERATIONS", "MANAGE_FIELD_OPERATIONS"))

    @staticmethod
    def _is_worker(user, activity):
        return getattr(activity, "employee_id", None) == user.id

    @classmethod
    def _assert_actor(cls, *, user, activity):
        if activity.company_id != user.company_id or not (cls._is_worker(user, activity) or cls._can_manage(user)):
            raise PermissionDenied("Field activity access denied.")

    @classmethod
    @transaction.atomic
    def start_activity(cls, *, activity, user, latitude=None, longitude=None, request=None):
        activity = type(activity).objects.select_for_update().get(pk=activity.pk)
        cls._assert_actor(user=user, activity=activity)
        if activity.status not in ("PLANNED", "ASSIGNED"):
            raise ValidationError("Activity cannot be started in its current state.")
        activity.status = "IN_PROGRESS"
        coordinates = cls._coordinates(latitude, longitude)
        if coordinates:
            activity.started_latitude, activity.started_longitude = coordinates
            activity.save(update_fields=["started_latitude", "started_longitude"])
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
        coordinates = cls._coordinates(latitude, longitude)
        if coordinates:
            stop.latitude, stop.longitude = coordinates
        stop.save(update_fields=["status", "arrived_at", "latitude", "longitude"])
        # Deliberately do NOT run stop-completion requirements here.
        create_audit_log(user=user, company=stop.activity.company, request=request, action="UPDATE", description="Field stop arrival recorded.", obj=stop)
        return stop

    @classmethod
    @transaction.atomic
    def complete_stop(cls, *, stop, user, notes="", validator=None, request=None):
        stop = type(stop).objects.select_for_update().select_related("activity").get(pk=stop.pk)
        cls._assert_actor(user=user, activity=stop.activity)
        if stop.status not in ("PENDING", "ARRIVED"):
            raise ValidationError("Stop cannot be completed in its current state.")
        from company_setup.models import FieldActivityTemplate
        required=FieldActivityTemplate.objects.filter(company=stop.activity.company,activity_type=stop.activity.activity_type,is_active=True,form_template__isnull=False).exists()
        if required and not stop.form_submission_id:
            raise ValidationError('Complete the configured field form before completing this stop.')
        if stop.form_submission_id:
            expected='APPROVED' if stop.form_submission.template.workflow_id else 'SUBMITTED'
            if stop.form_submission.status!=expected:
                raise ValidationError('Submit the field form and complete any required approval before completing this stop.')
        if validator:
            validator(stop)
        stop.status = "COMPLETED"
        stop.notes = notes or stop.notes
        stop.completed_at = timezone.now()
        stop.save(update_fields=["status", "completed_at", "notes"])
        create_audit_log(user=user, company=stop.activity.company, request=request, action="UPDATE", description="Field stop completed.", obj=stop)
        return stop

    @classmethod
    @transaction.atomic
    def complete_activity(cls, *, activity, user, latitude=None, longitude=None, validator=None, request=None):
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
        coordinates = cls._coordinates(latitude, longitude)
        if coordinates:
            activity.completed_latitude, activity.completed_longitude = coordinates
            activity.save(update_fields=["completed_latitude", "completed_longitude"])
        if hasattr(activity, "completed_at"):
            activity.completed_at = timezone.now()
            activity.save(update_fields=["status", "completed_at", "updated_at"])
        else:
            activity.save(update_fields=["status", "updated_at"])
        create_audit_log(user=user, company=activity.company, request=request, action="UPDATE", description="Field activity completed.", obj=activity)
        return activity


class FieldSummaryService:
    @staticmethod
    def employee_daily_summary(*, user, target_date):
        from .models import FieldActivity, FieldStop
        activities = FieldActivity.objects.filter(company_id=user.company_id, employee=user, activity_date=target_date)
        stops = FieldStop.objects.filter(activity__in=activities)
        return {"date": target_date.isoformat(), "total_activities": activities.count(),
                "completed_activities": activities.filter(status="COMPLETED").count(),
                "total_stops": stops.count(), "completed_stops": stops.filter(status="COMPLETED").count()}
