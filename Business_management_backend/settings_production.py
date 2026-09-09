from .settings import *  # noqa: F401,F403
from decouple import config

DEBUG = False
ALLOWED_HOSTS = [v.strip() for v in config("ALLOWED_HOSTS").split(",") if v.strip()]
CSRF_TRUSTED_ORIGINS = [v.strip() for v in config("CSRF_TRUSTED_ORIGINS", default="").split(",") if v.strip()]
CORS_ALLOWED_ORIGINS = [v.strip() for v in config("CORS_ALLOWED_ORIGINS", default="").split(",") if v.strip()]
CORS_ALLOW_ALL_ORIGINS = False

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "strict-origin-when-cross-origin"

DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

REDIS_URL = config("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 900
CELERY_TASK_SOFT_TIME_LIMIT = 840
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"

DEFAULT_FILE_STORAGE = "storages.backends.s3.S3Storage"
AWS_STORAGE_BUCKET_NAME = config("OBJECT_STORAGE_BUCKET")
AWS_S3_ENDPOINT_URL = config("OBJECT_STORAGE_ENDPOINT", default=None)
AWS_ACCESS_KEY_ID = config("OBJECT_STORAGE_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = config("OBJECT_STORAGE_SECRET_KEY")
AWS_QUERYSTRING_AUTH = True
AWS_QUERYSTRING_EXPIRE = 300
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"jsonish": {"format": "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "jsonish"}},
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
}
