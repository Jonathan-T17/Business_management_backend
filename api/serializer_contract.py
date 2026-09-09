from rest_framework import serializers
class ExplicitFieldsModelSerializer(serializers.ModelSerializer): pass
def assert_explicit_serializer(serializer_class):
    meta=getattr(serializer_class,'Meta',None)
    if meta and getattr(meta,'fields',None)=='__all__':
        raise AssertionError(f"{serializer_class.__module__}.{serializer_class.__name__} uses fields='__all__'.")
