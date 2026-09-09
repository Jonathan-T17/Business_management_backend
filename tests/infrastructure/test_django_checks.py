from django.core.management import call_command

def test_django_system_check():
    call_command('check')

def test_no_missing_model_changes():
    call_command('makemigrations', '--check', '--dry-run', verbosity=0)
