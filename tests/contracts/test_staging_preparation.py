import base64
from pathlib import Path
import pytest
import yaml
from deployment.check_staging import read_env, validate

ROOT = Path(__file__).resolve().parents[2]


def ready_values():
    values = read_env(ROOT/'deployment/.env.staging.example')
    values.update(SECRET_KEY='s'*64, DB_PASSWORD='d'*32,
                  ALLOWED_HOSTS='api.staging.acme.test', FRONTEND_URL='https://app.staging.acme.test',
                  CSRF_TRUSTED_ORIGINS='https://app.staging.acme.test', CORS_ALLOWED_ORIGINS='https://app.staging.acme.test',
                  OBJECT_STORAGE_BUCKET='acme-staging-private', OBJECT_STORAGE_ACCESS_KEY='test-only-access',
                  OBJECT_STORAGE_SECRET_KEY='test-only-secret', EMAIL_HOST='mail.staging.acme.test',
                  EMAIL_HOST_USER='test-only-user', EMAIL_HOST_PASSWORD='test-only-password',
                  DEFAULT_FROM_EMAIL='noreply@staging.acme.test', CLAMAV_IMAGE='clamav/clamav:test-only',
                  BACKUP_ENCRYPTION_KEY=base64.b64encode(b'k'*32).decode())
    return values


def test_template_is_not_deployable_and_completed_values_pass_offline():
    assert validate(read_env(ROOT/'deployment/.env.staging.example'))
    assert validate(ready_values()) == []


@pytest.mark.parametrize('key,value', [('DEBUG','True'),('SECURE_SSL_REDIRECT','False'),
    ('ATTACHMENT_SCAN_REQUIRED','False'),('OBJECT_STORAGE_BUCKET','production-private'),
    ('DB_NAME','production'),('CORS_ALLOWED_ORIGINS','*'),('SECRET_KEY','short'),
    ('BACKUP_ENCRYPTION_KEY','not-a-key'),('CLAMAV_IMAGE','unreviewed/scanner:latest')])
def test_staging_preflight_rejects_unsafe_values(key,value):
    values=ready_values();values[key]=value
    assert any(key in issue for issue in validate(values))


def test_compose_is_private_and_does_not_import_production_settings():
    stack=yaml.safe_load((ROOT/'deployment/docker-compose.staging.yml').read_text())
    for name in ('db','redis','clamav','worker','scheduler'):
        assert 'ports' not in stack['services'][name]
    assert stack['services']['backend']['ports']==['127.0.0.1:18000:8000']
    for name in ('backend','worker','scheduler'):
        assert stack['services'][name]['env_file']=='../.env.staging'
    assert stack['networks']['upload_scanning']['internal'] is True
    assert 'upload_scanning' in stack['services']['worker']['networks']
