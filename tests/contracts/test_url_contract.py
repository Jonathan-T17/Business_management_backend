import pytest
from django.urls import resolve, Resolver404

def test_canonical_auth_route():
    assert resolve('/api/v1/auth/token/').url_name == 'token-obtain'

def test_canonical_dashboard_route():
    assert resolve('/api/v1/dashboard/').url_name == 'dashboard'

def test_platform_v1_route_exists():
    assert resolve('/api/platform/v1/dashboard/').url_name == 'platform-dashboard'

def test_legacy_auth_route_removed():
    with pytest.raises(Resolver404):
        resolve('/api/token/')

def test_legacy_platform_route_removed():
    with pytest.raises(Resolver404):
        resolve('/api/platform/dashboard/')

def test_internal_admin_route_exists():
    assert resolve('/internal/admin/')
