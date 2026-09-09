from pathlib import Path
from rest_framework.exceptions import ValidationError
DEFAULT_MAX_BYTES=20*1024*1024
BLOCKED_EXTENSIONS={'.exe','.dll','.bat','.cmd','.ps1','.sh','.com','.scr','.msi'}
class UploadValidationService:
    @classmethod
    def validate(cls,upload,*,max_bytes=DEFAULT_MAX_BYTES,allowed_mime_types=None):
        if not upload: raise ValidationError({'file':'File is required.'})
        if upload.size>max_bytes: raise ValidationError({'file':'File exceeds the permitted size.'})
        if Path(upload.name or '').suffix.lower() in BLOCKED_EXTENSIONS: raise ValidationError({'file':'This file type is not permitted.'})
        if allowed_mime_types and getattr(upload,'content_type','') not in allowed_mime_types: raise ValidationError({'file':'Unsupported content type.'})
        return upload
