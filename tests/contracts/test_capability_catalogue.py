"""Prevent partial overlays from removing capabilities used by installed apps."""
import ast
from pathlib import Path

from django.apps import apps
from core.capabilities import Capabilities


def missing_references(source, known):
    tree = ast.parse(source)
    aliases = {
        item.asname or item.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == 'core.capabilities'
        for item in node.names if item.name == 'Capabilities'
    }
    return [(node.lineno, node.attr) for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
            and node.value.id in aliases and node.attr.isupper() and node.attr not in known]


def test_installed_app_capability_references_are_defined():
    root = Path(__file__).resolve().parents[2]
    errors = []
    for app in apps.get_app_configs():
        directory = Path(app.path).resolve()
        if directory.parent != root:
            continue
        for file in directory.rglob('*.py'):
            for line, name in missing_references(file.read_text(encoding='utf-8-sig'), vars(Capabilities)):
                errors.append(f'{file.relative_to(root)}:{line}: {name}')
    assert not errors, '\n'.join(errors)


def test_scanner_detects_missing_alias_reference_without_reading_comments():
    source = '''from core.capabilities import Capabilities as C
# C.COMMENT_ONLY
permission = C.REMOVED_PERMISSION
'''
    assert missing_references(source, {'USE_FORMS'}) == [(3, 'REMOVED_PERMISSION')]


def test_catalogue_groups_only_contain_defined_capabilities():
    known = set(Capabilities.values())
    assert Capabilities.PLATFORM_ONLY <= known
    assert Capabilities.SENSITIVE <= known
    for preset in Capabilities.PRESETS.values():
        assert set(preset) <= known
        assert not set(preset) & Capabilities.PLATFORM_ONLY
    assert all(not Capabilities.is_assignable_by_company_admin(code)
               for code in Capabilities.PLATFORM_ONLY)
