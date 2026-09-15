from django.core.management import call_command
import pytest

def test_django_system_check():
    call_command('check')

@pytest.mark.django_db
def test_no_missing_model_changes():
    call_command('makemigrations', '--check', '--dry-run', verbosity=0)
