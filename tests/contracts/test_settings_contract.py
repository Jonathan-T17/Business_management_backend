from django.conf import settings

def test_blacklist_rotation_not_in_rest_framework():
    assert 'BLACKLIST_AFTER_ROTATION' not in settings.REST_FRAMEWORK

def test_refresh_rotation_and_blacklisting_enabled():
    assert settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS') is True
    assert settings.SIMPLE_JWT.get('BLACKLIST_AFTER_ROTATION') is True

def test_default_pagination_configured():
    assert settings.REST_FRAMEWORK.get('DEFAULT_PAGINATION_CLASS')
    assert int(settings.REST_FRAMEWORK.get('PAGE_SIZE', 0)) > 0

def test_custom_exception_handler_configured():
    assert settings.REST_FRAMEWORK.get('EXCEPTION_HANDLER') == 'api.errors.smartbiz_exception_handler'

def test_request_id_middleware_installed():
    assert 'api.request_id.RequestIDMiddleware' in settings.MIDDLEWARE

def test_no_global_urlpath_versioning_required():
    assert 'DEFAULT_VERSIONING_CLASS' not in settings.REST_FRAMEWORK
