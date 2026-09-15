"""Check actual TypeScript client calls/capability constants against Django (no HTTP)."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend', type=Path, default=ROOT.parent / 'business_management_frontend')
    parser.add_argument('--report', type=Path, help='Optional report path; omitted means read-only validation')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Business_management_backend.settings')
    import django
    django.setup()
    from django.urls import resolve, Resolver404
    from core.capabilities import Capabilities
    run = subprocess.run(['node', str(ROOT/'scripts/scan_frontend_contracts.cjs'), str(args.frontend.resolve())], text=True, encoding='utf-8', capture_output=True)
    if run.returncode:
        print(run.stderr); return 2
    scan = json.loads(run.stdout)
    if not scan['calls'] or not scan['capabilities']:
        print('FAIL: no client calls or capability constants discovered; check the frontend path/layout.')
        return 1
    known = {value for name,value in vars(Capabilities).items() if name.isupper() and isinstance(value,str)}
    unknown = sorted(set(scan['capabilities'])-known)
    failed=[]
    for call in scan['calls']:
        groups = {}
        for path in call['paths']:
            key = path.replace('00000000-0000-0000-0000-000000000001', '1')
            groups.setdefault(key, []).append(path)
        for paths in groups.values():
            if not any(route_supports(path, call['method'], resolve, Resolver404) for path in paths):
                failed.append({**call, 'path': ' | '.join(paths)})
    lines=['# Frontend contract checks','',f"Parsed {len(scan['calls'])} client calls and {len(scan['capabilities'])} capability constants.",
           'Covers imported API client aliases and generic calls using the TypeScript parser. Dynamic expressions use example IDs; runtime payload/response/permission checks require integration tests.',
           '',f'Unknown capabilities: {unknown}',f'Unresolved calls: {len(failed)}',f'Computed calls requiring manual review: {len(scan["skipped"])}','']
    for item in failed: lines.append(f"- FAIL {item['file']}:{item['line']} {item['method'].upper()} {item['path']}")
    for item in scan['skipped']: lines.append(f"- REVIEW {item['file']}:{item['line']} {item['method'].upper()} {item['path']}")
    report='\n'.join(lines)+'\n'
    print(report)
    if args.report: args.report.write_text(report,encoding='utf-8')
    return 1 if failed or unknown or scan['skipped'] else 0


def route_supports(path, method, resolve, resolver_error):
    try:
        match = resolve(path.split('?')[0])
    except resolver_error:
        return False
    actions = getattr(match.func, 'actions', None)
    view = getattr(match.func, 'cls', getattr(match.func, 'view_class', None))
    return bool((actions and method in actions) or (not actions and view and hasattr(view, method)))

if __name__ == '__main__': raise SystemExit(main())
