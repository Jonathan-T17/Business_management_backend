"""Run cross-application regression checks; --full adds the complete suite and build."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend', type=Path, default=ROOT.parent / 'business_management_frontend')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    frontend = args.frontend.resolve()
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm or not (frontend / 'package.json').is_file():
        print('Node/npm and a complete frontend checkout are required.')
        return 2
    checks = [
        (ROOT, [sys.executable, 'scripts/verify_frontend_contracts.py', '--frontend', str(frontend)]),
        (ROOT, [sys.executable, 'manage.py', 'check']),
        (ROOT, [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run']),
        (ROOT, [sys.executable, '-m', 'pytest', '-q'] + ([] if args.full else [
            'tests/contracts', 'tests/security/test_form_governance.py',
            'tests/security/test_login_flow.py'])),
        (frontend, [npm, 'run', 'typecheck']),
        (frontend, [npm, 'run', 'lint']),
    ]
    if args.full:
        checks.append((frontend, [npm, 'run', 'build']))
    for cwd, command in checks:
        print('Checking: ' + ' '.join(command), flush=True)
        result = subprocess.run(command, cwd=cwd)
        if result.returncode:
            return result.returncode
    print('Selected checks passed. Authenticated UI and deployed infrastructure need separate verification.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
