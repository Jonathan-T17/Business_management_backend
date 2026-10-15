from unittest.mock import patch
import pytest
from django.core.management import call_command, CommandError
from django.test import override_settings


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_one_cycle_runs_reporting_and_probes():
    with patch("platform_admin.management.commands.run_local_automation.process_reporting") as reporting, patch("platform_admin.management.commands.run_local_automation.run_service_checks") as probes:
        call_command("run_local_automation", once=True)
        reporting.assert_called_once()
        probes.assert_called_once()
        # The lock is released, allowing the next invocation.
        call_command("run_local_automation", once=True)
        assert reporting.call_count == 2


@override_settings(DEBUG=False)
def test_production_refuses_development_runner():
    with pytest.raises(CommandError, match="production Celery"):
        call_command("run_local_automation", once=True)


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_failure_is_not_reported_as_success_and_releases_lock():
    with patch("platform_admin.management.commands.run_local_automation.process_reporting", side_effect=RuntimeError), patch("platform_admin.management.commands.run_local_automation.run_service_checks") as probes:
        with pytest.raises(CommandError, match="Reporting failed"):
            call_command("run_local_automation", once=True)
        probes.assert_not_called()
    with patch("platform_admin.management.commands.run_local_automation.process_reporting"), patch("platform_admin.management.commands.run_local_automation.run_service_checks"):
        call_command("run_local_automation", once=True)
