from datetime import datetime, time, timedelta, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.core.management import call_command
from companies.models import Company
from forms_engine.models import FormTemplate, FormSubmission
from notifications.models import Notification
from reporting_schedules.models import ReportingObligation, ReportingSchedule
from reporting_schedules.services import ReportingReminderService


@pytest.fixture
def scheduled_report(django_user_model):
    company = Company.objects.create(name="Pacific company", timezone="Pacific/Kiritimati")
    user = django_user_model.objects.create_user(email="jobs@example.test", company=company, role="EMPLOYEE", is_active=True, account_state="ACTIVE")
    template = FormTemplate.objects.create(company=company, name="Daily", code="daily", lifecycle_status="PUBLISHED")
    schedule = ReportingSchedule.objects.create(
        company=company, template=template, name="Daily", frequency="DAILY",
        target_type="USER", target_user=user, start_date="2026-01-01", due_time=time(17),
    )
    return company, user, schedule


@pytest.mark.django_db
def test_generation_command_uses_company_date_and_is_repeatable(scheduled_report):
    company, user, schedule = scheduled_report
    now = datetime(2026, 9, 17, 12, tzinfo=dt_timezone.utc)
    with patch("reporting_schedules.management.commands.generate_reporting_obligations.timezone.now", return_value=now):
        call_command("generate_reporting_obligations")
        call_command("generate_reporting_obligations")
    obligation = ReportingObligation.objects.get(schedule=schedule)
    assert str(obligation.reporting_date) == "2026-09-18"
    assert obligation.due_at == datetime(2026, 9, 18, 3, tzinfo=dt_timezone.utc)


@pytest.mark.django_db
def test_reminders_respect_local_morning_and_do_not_repeat(scheduled_report):
    company, user, schedule = scheduled_report
    morning = datetime(2026, 9, 17, 18, tzinfo=dt_timezone.utc)  # 08:00 next day locally
    obligation = ReportingObligation.objects.create(
        company=company, user=user, schedule=schedule, reporting_date="2026-09-18",
        due_at=morning + timedelta(hours=9),
    )
    assert ReportingReminderService.send_pending(now=morning - timedelta(minutes=1)) == 0
    assert ReportingReminderService.send_pending(now=morning) == 1
    assert ReportingReminderService.send_pending(now=morning) == 0
    assert ReportingReminderService.send_pending(now=obligation.due_at - timedelta(minutes=30)) == 1
    assert ReportingReminderService.send_pending(now=obligation.due_at - timedelta(minutes=20)) == 0
    assert Notification.objects.filter(recipient=user).count() == 2


@pytest.mark.django_db
def test_reminder_failure_rolls_back_flag(scheduled_report):
    company, user, schedule = scheduled_report
    now = datetime(2026, 9, 17, 18, tzinfo=dt_timezone.utc)
    obligation = ReportingObligation.objects.create(
        company=company, user=user, schedule=schedule, reporting_date="2026-09-18",
        due_at=now + timedelta(minutes=30),
    )
    with patch("notifications.services.create_notification", side_effect=RuntimeError("Unavailable")):
        with pytest.raises(RuntimeError):
            ReportingReminderService.send_pending(now=now)
    obligation.refresh_from_db()
    assert not obligation.final_reminder_sent
    assert ReportingReminderService.send_pending(now=now) == 1


@pytest.mark.django_db
def test_moved_user_does_not_receive_old_company_reminder(scheduled_report):
    company, user, schedule = scheduled_report
    now = datetime(2026, 9, 17, 18, tzinfo=dt_timezone.utc)
    ReportingObligation.objects.create(company=company, user=user, schedule=schedule,
        reporting_date="2026-09-18", due_at=now + timedelta(minutes=30))
    user.company = Company.objects.create(name="Other")
    user.save(update_fields=["company"])
    assert ReportingReminderService.send_pending(now=now) == 0
    assert not Notification.objects.filter(recipient=user).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("submission_status,expected", [("DRAFT", "MISSED"), ("SUBMITTED", "DRAFT")])
def test_overdue_command_handles_linked_submissions(scheduled_report, submission_status, expected):
    company, user, schedule = scheduled_report
    now = datetime(2026, 9, 17, 18, tzinfo=dt_timezone.utc)
    submission = FormSubmission.objects.create(company=company, template=schedule.template,
        submitted_by=user, reference_number="job-test", status=submission_status)
    obligation = ReportingObligation.objects.create(company=company, user=user, schedule=schedule,
        reporting_date="2026-09-17", due_at=now - timedelta(minutes=1), status="DRAFT", submission=submission)
    with patch("reporting_schedules.services.timezone.now", return_value=now):
        call_command("mark_overdue_reporting")
        call_command("mark_overdue_reporting")
    obligation.refresh_from_db()
    assert obligation.status == expected
