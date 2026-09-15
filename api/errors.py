import uuid
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

def smartbiz_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
    response = drf_exception_handler(exc, context)
    if response is None:
        return response
    request_id = getattr(context.get('request'), 'request_id', None) or str(uuid.uuid4())
    if isinstance(exc, ValidationError):
        code, message, errors = 'VALIDATION_ERROR', 'One or more fields are invalid.', response.data
    else:
        code = str(getattr(exc, 'default_code', None) or 'API_ERROR').upper()
        detail = response.data.get('detail') if isinstance(response.data, dict) else None
        message, errors = str(detail or 'The request could not be completed.'), None
    payload = {'error': {'code': code, 'message': message, 'request_id': request_id}}
    if errors is not None:
        payload['error']['fields'] = errors
    response.data = payload
    return response
