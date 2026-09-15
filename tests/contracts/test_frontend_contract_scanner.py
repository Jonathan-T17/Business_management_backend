import json
from pathlib import Path
import shutil
import subprocess

import pytest


def test_scanner_handles_aliases_generics_and_conditional_routes(tmp_path):
    root = Path(__file__).resolve().parents[2]
    frontend = root.parent / 'business_management_frontend'
    if not shutil.which('node') or not (frontend / 'node_modules/typescript').exists():
        pytest.skip('Requires Node and frontend TypeScript installation')
    (tmp_path / 'src/api').mkdir(parents=True)
    (tmp_path / 'src/utils').mkdir()
    (tmp_path / 'src/api/example.ts').write_text('''
import {apiClient as api, platformClient as platform} from "./client";
api.get<Result>(`forms/${id}/`);
platform.post(enabled ? "plans/" : "subscriptions/", {});
api.get(computedPath);
''', encoding='utf-8')
    (tmp_path / 'src/utils/capabilities.ts').write_text(
        'export const CAPABILITIES = {USE_FORMS: "USE_FORMS"} as const;', encoding='utf-8')
    run = subprocess.run(['node', str(root / 'scripts/scan_frontend_contracts.cjs'),
                          str(tmp_path), str(frontend)], capture_output=True, text=True, check=True)
    data = json.loads(run.stdout)
    assert data['capabilities'] == ['USE_FORMS']
    assert len(data['calls']) == 2
    assert '/api/v1/forms/1/' in data['calls'][0]['paths']
    assert data['calls'][1]['paths'] == ['/api/platform/v1/plans/', '/api/platform/v1/subscriptions/']
    assert len(data['skipped']) == 1
