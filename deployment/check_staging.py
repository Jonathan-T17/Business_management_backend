"""Offline staging checks. Never connects to services or prints credential values."""
import argparse
import base64
from pathlib import Path
from urllib.parse import urlsplit


def read_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError('Each non-comment line must contain KEY=value.')
        key, value = line.split('=', 1)
        if key in values:
            raise ValueError(f'Duplicate setting: {key}')
        values[key] = value.strip().strip('\"\'')
    return values


def validate(values):
    issues = []
    required = ('SECRET_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'ALLOWED_HOSTS',
                'FRONTEND_URL', 'OBJECT_STORAGE_BUCKET', 'OBJECT_STORAGE_ACCESS_KEY',
                'OBJECT_STORAGE_SECRET_KEY', 'EMAIL_HOST', 'EMAIL_HOST_USER',
                'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL', 'CLAMAV_IMAGE', 'BACKUP_ENCRYPTION_KEY')
    for key in required:
        value = values.get(key, '')
        if not value or any(token in value.lower() for token in ('replace-', 'replace_me', 'example.com')):
            issues.append(f'{key}: supply a real staging-only value.')
    expected = {
        'DJANGO_SETTINGS_MODULE': 'Business_management_backend.settings_production',
        'DEBUG': 'False', 'SECURE_SSL_REDIRECT': 'True', 'ATTACHMENT_SCAN_REQUIRED': 'True',
        'ATTACHMENT_SCANNER': 'documents.scanning.clamav', 'CLAMAV_HOST': 'clamav',
        'CLAMAV_PORT': '3310', 'DB_HOST': 'db', 'DB_PORT': '5432',
        'REDIS_URL': 'redis://redis:6379/0', 'EMAIL_USE_TLS': 'True', 'BACKUP_DIRECTORY': '/backups',
    }
    for key, value in expected.items():
        if values.get(key) != value:
            issues.append(f'{key}: does not match the secure standalone staging stack.')
    for key in ('DB_NAME', 'DB_USER', 'OBJECT_STORAGE_BUCKET'):
        if 'staging' not in values.get(key, '').lower():
            issues.append(f'{key}: use an explicitly staging-named resource.')
    for key, minimum in (('SECRET_KEY', 50), ('DB_PASSWORD', 24)):
        if len(values.get(key, '')) < minimum:
            issues.append(f'{key}: generate a new value with at least {minimum} characters.')
    try:
        if len(base64.b64decode(values.get('BACKUP_ENCRYPTION_KEY', ''), validate=True)) != 32:
            raise ValueError()
    except (ValueError, TypeError):
        issues.append('BACKUP_ENCRYPTION_KEY: supply a base64-encoded 32-byte key.')
    frontend = values.get('FRONTEND_URL', '')
    url = urlsplit(frontend)
    if url.scheme != 'https' or not url.hostname or url.path not in ('', '/') or url.query or url.fragment or url.username:
        issues.append('FRONTEND_URL: use the HTTPS staging origin without a path.')
    for key in ('CSRF_TRUSTED_ORIGINS', 'CORS_ALLOWED_ORIGINS'):
        if values.get(key, '').rstrip('/') != frontend.rstrip('/'):
            issues.append(f'{key}: must match the staging frontend origin exactly.')
    if '*' in values.get('ALLOWED_HOSTS', '') or 'localhost' in values.get('ALLOWED_HOSTS', ''):
        issues.append('ALLOWED_HOSTS: use only the actual staging API hostname.')
    image = values.get('CLAMAV_IMAGE', '')
    if not image.startswith(('clamav/clamav:', 'clamav/clamav@sha256:')):
        issues.append('CLAMAV_IMAGE: choose a reviewed official ClamAV image reference.')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env', default='.env.staging')
    options = parser.parse_args()
    try:
        issues = validate(read_env(options.env))
    except (OSError, ValueError):
        print('Unable to read staging settings. Check the file path and KEY=value syntax.')
        return 1
    for issue in issues:
        print(issue)
    if issues:
        return 1
    print('Offline settings checks passed. Credentials, TLS, service reachability and resource isolation still need host verification.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
