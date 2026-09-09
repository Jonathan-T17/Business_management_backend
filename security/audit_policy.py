SENSITIVE_KEYS={'password','password_hash','otp','otp_code','token','refresh_token','access_token','secret','latitude','longitude','salary','base_salary','compensation','medical','private_message','private_message_body'}
IDENTITY_KEYS_FOR_ANONYMOUS={'created_by','created_by_id','created_by_email','submitted_by','submitted_by_id','submitted_by_email','requester','requester_id','requester_email'}
class AuditMetadataPolicy:
    @classmethod
    def sanitize(cls,metadata,*,anonymous_source=False):
        out={}
        for k,v in (metadata or {}).items():
            lower=k.lower()
            if lower in SENSITIVE_KEYS or (anonymous_source and lower in IDENTITY_KEYS_FOR_ANONYMOUS):continue
            out[k]=v
        return out
