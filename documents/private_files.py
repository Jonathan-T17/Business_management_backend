from datetime import timedelta
from django.utils import timezone


class PrivateFileAccessService:
    """Storage backend adapter. Never expose raw FileField URLs in serializers."""

    DEFAULT_TTL = timedelta(minutes=5)

    @classmethod
    def descriptor(cls, *, file_obj, filename, mime_type, size):
        return {
            "filename": filename,
            "mime_type": mime_type,
            "size": size,
            "download_url": None,
            "download_expires_at": None,
        }

    @classmethod
    def signed_download(cls, *, storage, name, ttl=None):
        ttl = ttl or cls.DEFAULT_TTL
        # Production S3/GCS/Azure storage adapter should implement signed_url().
        if not hasattr(storage, "signed_url"):
            raise RuntimeError("Private storage backend must provide signed_url().")
        expires_at = timezone.now() + ttl
        return storage.signed_url(name, expires_in=int(ttl.total_seconds())), expires_at
