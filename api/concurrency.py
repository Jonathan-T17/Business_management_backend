from django.db import transaction
from rest_framework.exceptions import APIException, ValidationError
class Conflict(APIException):
    status_code=409; default_detail='The resource changed since you last loaded it.'; default_code='conflict'
class VersionedUpdateService:
    @classmethod
    @transaction.atomic
    def lock_and_check(cls, *, model, pk, expected_version):
        if expected_version is None: raise ValidationError({'version':'Current resource version is required.'})
        obj=model.objects.select_for_update().get(pk=pk); actual=getattr(obj,'version',None)
        if actual is None: raise RuntimeError(f'{model.__name__} is not versioned.')
        if int(expected_version)!=int(actual): raise Conflict()
        return obj
    @staticmethod
    def bump(obj): obj.version+=1; return obj
