import inspect, importlib
from rest_framework import serializers

PUBLIC_APPS = (
    'users','companies','organizations','projects','tasks','reports','comments',
    'notifications','subscriptions','analytics_ai','chat','workflows','forms_engine',
    'documents','reporting_schedules','planning','requests_app','field_operations',
    'records_management','data_tools','company_setup','support','platform_admin',
)

def test_no_public_model_serializer_uses_all_fields():
    offenders = []
    for app in PUBLIC_APPS:
        try:
            module = importlib.import_module(f'{app}.serializers')
        except ModuleNotFoundError:
            continue
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if not issubclass(cls, serializers.BaseSerializer):
                continue
            meta = getattr(cls, 'Meta', None)
            if meta and getattr(meta, 'fields', None) == '__all__':
                offenders.append(f'{cls.__module__}.{cls.__name__}')
    assert not offenders, "fields='__all__' is forbidden: " + ', '.join(offenders)
