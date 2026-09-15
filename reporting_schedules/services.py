from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError


class ReportingScheduleValidator:
    TARGET_FIELD = {
        "USER": "target_user",
        "ROLE": "target_role",
        "BRANCH": "target_branch",
        "DEPARTMENT": "target_department",
        "TEAM": "target_team",
        "POSITION": "target_position",
    }

    @classmethod
    def validate(cls, *, company, data):
        target_type = data.get("target_type")
        required = cls.TARGET_FIELD.get(target_type)
        if not required:
            raise ValidationError({"target_type": "Invalid target type."})
        for field in cls.TARGET_FIELD.values():
            value = data.get(field)
            if field == required and not value:
                raise ValidationError({field: "This target is required."})
            if field != required and value not in (None, ""):
                raise ValidationError({field: "This target does not apply to the selected target type."})
        value = data[required]
        if target_type != "ROLE" and getattr(value, "company_id", None) != company.id:
            raise ValidationError({required: "Target must belong to this company."})

        frequency = data.get("frequency")
        weekday = data.get("weekday")
        day = data.get("day_of_month")
        if frequency == "WEEKLY" and (weekday is None or not 0 <= weekday <= 6):
            raise ValidationError({"weekday": "Weekly schedules require weekday 0-6."})
        if frequency == "MONTHLY" and (day is None or not 1 <= day <= 31):
            raise ValidationError({"day_of_month": "Monthly schedules require a day from 1 to 31."})
        if frequency == "CUSTOM" and not data.get("custom_rule"):
            raise ValidationError({"custom_rule": "Custom schedules require an implemented custom rule."})


class ReportingScheduleService:
    @staticmethod
    def company_zone(company):
        try:
            return ZoneInfo(company.timezone or "UTC")
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def local_date(company, now=None):
        return (now or timezone.now()).astimezone(ReportingScheduleService.company_zone(company)).date()

    @staticmethod
    def local_due_at(company, target_date, due_time):
        local = datetime.combine(target_date, due_time or time(17, 0), tzinfo=ReportingScheduleService.company_zone(company))
        return local.astimezone(ZoneInfo("UTC"))

    @staticmethod
    def applies_on_date(schedule, target_date):
        if target_date < schedule.start_date or (schedule.end_date and target_date > schedule.end_date):
            return False
        if schedule.frequency == "DAILY":
            return True
        if schedule.frequency == "WEEKLY":
            return schedule.weekday == target_date.weekday()
        if schedule.frequency == "MONTHLY":
            # Months shorter than configured day use the final calendar day only when explicitly enabled.
            if schedule.day_of_month == target_date.day:
                return True
            return False
        if schedule.frequency == "CUSTOM":
            from reporting_schedules.custom_rules import CustomScheduleRuleEngine
            return CustomScheduleRuleEngine.applies(schedule.custom_rule, target_date)
        return False

    @classmethod
    @transaction.atomic
    def generate_for_company_now(cls, *, company, now=None):
        from reporting_schedules.models import ReportingSchedule, ReportingObligation

        target_date = cls.local_date(company, now=now)
        created = []
        for schedule in ReportingSchedule.objects.filter(company=company, is_active=True).select_related("template"):
            if not cls.applies_on_date(schedule, target_date):
                continue
            if schedule.template.lifecycle_status != "PUBLISHED" or not schedule.template.is_active:
                continue
            due_at = cls.local_due_at(company, target_date, schedule.due_time)
            for user in cls.resolve_users(schedule):
                obligation, made = ReportingObligation.objects.get_or_create(
                    schedule=schedule,
                    user=user,
                    reporting_date=target_date,
                    defaults={
                        "company": company,
                        "due_at": due_at,
                        "status": "PENDING",
                    },
                )
                if made:
                    created.append(obligation)
        return created

    @staticmethod
    def resolve_users(schedule):
        from users.models import User
        users = User.objects.filter(company=schedule.company, is_active=True, is_deleted=False, is_superuser=False).exclude(role="SUPERUSER")
        filters = {
            "USER": {"pk": schedule.target_user_id}, "ROLE": {"role": schedule.target_role},
            "BRANCH": {"branch_id": schedule.target_branch_id},
            "DEPARTMENT": {"employee_profile__department_id": schedule.target_department_id},
            "TEAM": {"employee_profile__team_id": schedule.target_team_id},
            "POSITION": {"employee_profile__position_id": schedule.target_position_id},
        }
        selected = filters.get(schedule.target_type)
        if not selected or not all(selected.values()):
            return users.none()
        return users.filter(**selected)


class ReportingObligationService:
    @classmethod
    @transaction.atomic
    def start_submission(cls, *, obligation, user):
        from reporting_schedules.models import ReportingObligation
        from forms_engine.services import FormSubmissionService
        from core.authorization import Authorization

        obligation = ReportingObligation.objects.select_for_update().select_related("schedule__template").get(pk=obligation.pk)
        if obligation.user_id != user.pk or obligation.company_id != user.company_id or not Authorization.can_authenticate(user):
            raise ValidationError("This reporting obligation is not available to you.")
        if obligation.status not in {"PENDING", "DRAFT", "RETURNED", "MISSED"}:
            raise ValidationError("This reporting obligation cannot be started.")
        if timezone.now() > obligation.due_at and not obligation.schedule.allow_late_submission:
            raise ValidationError("Late submission is not allowed for this reporting process.")
        if obligation.submission_id:
            return obligation.submission
        submission = FormSubmissionService.create_submission(
            template=obligation.schedule.template, user=user,
            reporting_date=obligation.reporting_date, title=obligation.schedule.name,
        )
        obligation.submission = submission
        obligation.status = "DRAFT"
        obligation.save(update_fields=["submission", "status"])
        return submission


class ReportingObligationStateService:
    @classmethod
    @transaction.atomic
    def mark_submitted(cls, *, obligation, submitted_at):
        from reporting_schedules.models import ReportingObligation

        obligation = ReportingObligation.objects.select_for_update().get(pk=obligation.pk)
        if obligation.status in {"CANCELLED", "APPROVED", "REJECTED"}:
            raise ValidationError("This reporting obligation is finalized.")
        late = submitted_at > obligation.due_at
        if late and not obligation.schedule.allow_late_submission:
            raise ValidationError("Late submission is not allowed for this reporting process.")
        obligation.status = "LATE" if late else "SUBMITTED"
        obligation.submitted_at = submitted_at
        obligation.save(update_fields=["status", "submitted_at"])
        return obligation

    @classmethod
    @transaction.atomic
    def mark_overdue(cls, *, now=None):
        from reporting_schedules.models import ReportingObligation

        now = now or timezone.now()
        queryset = ReportingObligation.objects.select_for_update().filter(
            status__in=["PENDING", "DRAFT"],
            due_at__lt=now,
        )
        count = 0
        for obligation in queryset:
            # A linked draft submission does not prevent an obligation from becoming missed.
            if obligation.submission_id and obligation.submission.status in {"SUBMITTED", "UNDER_REVIEW", "APPROVED"}:
                continue
            obligation.status = "MISSED"
            obligation.save(update_fields=["status"])
            count += 1
        return count
