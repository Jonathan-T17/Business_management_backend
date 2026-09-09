import hashlib, json
from dataclasses import dataclass
from django.core.cache import cache
from rest_framework.exceptions import ValidationError
@dataclass(frozen=True)
class IdempotencyReplay:
    status_code:int; body:dict
class IdempotencyService:
    ttl_seconds=86400
    @classmethod
    def key(cls, *, user, route, key):
        digest=hashlib.sha256(f"{getattr(user,'id','')}:{route}:{key}".encode()).hexdigest()
        return f'smartbiz:idempotency:{digest}'
    @classmethod
    def require_key(cls, request):
        value=(request.headers.get('Idempotency-Key') or '').strip()
        if not value or len(value)>128: raise ValidationError({'idempotency_key':'A valid Idempotency-Key header is required.'})
        return value
    @classmethod
    def fingerprint(cls, request):
        return hashlib.sha256(json.dumps(request.data,sort_keys=True,default=str).encode()).hexdigest()
    @classmethod
    def lookup(cls, *, request, route):
        key=cls.require_key(request); ck=cls.key(user=request.user,route=route,key=key); stored=cache.get(ck)
        if not stored: return ck,None
        if stored['fingerprint']!=cls.fingerprint(request): raise ValidationError({'idempotency_key':'This key was already used with a different request.'})
        return ck,IdempotencyReplay(stored['status_code'],stored['body'])
    @classmethod
    def store(cls, *, cache_key, request, status_code, body):
        cache.set(cache_key,{'fingerprint':cls.fingerprint(request),'status_code':status_code,'body':body},timeout=cls.ttl_seconds)
