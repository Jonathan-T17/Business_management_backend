"""Map literal frontend API calls to Django URL/method registrations (no HTTP)."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Business_management_backend.settings')
import django
django.setup()
from django.urls import Resolver404, resolve

frontend = ROOT.parent / 'business_management_frontend' / 'src' / 'api'
pattern = re.compile(r'(apiClient|platformClient)\.(get|post|patch|put|delete)(?:<[^;]*?>)?\(\s*([\"\x27`])(.+?)\3', re.S)
rows = set()
for source in frontend.glob('*.ts'):
    for match in pattern.finditer(source.read_text(encoding='utf-8')):
        client, method, _, path = match.groups()
        if '\n' in path or len(path) > 180:
            continue
        prefix = '/api/platform/v1/' if client == 'platformClient' else '/api/v1/'
        variants = [path]
        conditional = re.search(r'\$\{[^}]+\?\s*"([^"]+)"\s*:\s*"([^"]+)"\}', path)
        if conditional:
            variants = [path.replace(conditional.group(0), value) for value in conditional.groups()]
        for variant in variants:
            matched = None
            for value in ['1', '00000000-0000-0000-0000-000000000001']:
                candidate = prefix + re.sub(r'\$\{[^}]+\}', value, variant).split('?')[0]
                try:
                    matched = resolve(candidate)
                    break
                except Resolver404:
                    pass
            result = 'Unresolved'
            if matched:
                actions = getattr(matched.func, 'actions', None)
                view = getattr(matched.func, 'cls', None)
                result = 'Route and method found' if ((actions and method in actions) or (view and hasattr(view, method))) else 'Route found; inspect method'
            rows.add((source.name, method.upper(), prefix + variant, result))
lines = ['# Frontend API route audit', '', 'Static URL/method resolution only. Numeric and UUID examples replace dynamic identifiers. This does not validate payloads, response fields, permissions, or live workflows. Computed URLs and clients other than apiClient/platformClient need manual inspection.', '', '| Module | Method | Path | Result |', '|---|---|---|---|']
lines += ['| ' + ' | '.join(row) + ' |' for row in sorted(rows)]
(ROOT / 'deployment' / 'FRONTEND_API_ROUTE_AUDIT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'{len(rows)} unique literal calls mapped; {sum(row[-1] != "Route and method found" for row in rows)} require review.')
