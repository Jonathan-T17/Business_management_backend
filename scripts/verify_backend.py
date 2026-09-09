#!/usr/bin/env python
import os, subprocess, sys

COMMANDS = [
    [sys.executable, 'manage.py', 'check'],
    [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
    [sys.executable, 'manage.py', 'migrate', '--plan'],
    [sys.executable, '-m', 'pytest', '-q'],
    [sys.executable, 'manage.py', 'spectacular', '--file', 'openapi-v1.yaml', '--validate'],
]

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Business_management_backend.settings')
    for cmd in COMMANDS:
        print('+', ' '.join(cmd), flush=True)
        result = subprocess.run(cmd)
        if result.returncode:
            return result.returncode
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
