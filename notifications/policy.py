from urllib.parse import urlparse
from core.secondary_policy import SecondaryDataPolicy
class NotificationAudience:
    PERSONAL_SECURITY="PERSONAL_SECURITY";TENANT_SECURITY="TENANT_SECURITY";PLATFORM_SECURITY="PLATFORM_SECURITY";OPERATIONAL="OPERATIONAL"
class NotificationPolicyService:
    @staticmethod
    def safe_internal_url(url):
        if not url:return ""
        p=urlparse(url)
        return "" if p.scheme or p.netloc or not url.startswith("/") else url
    @classmethod
    def safe_message(cls,*,classification="NORMAL",message=""):
        return SecondaryDataPolicy.notification_preview(classification=classification,safe_message=message)
    @staticmethod
    def audience_for_event(event_type):
        if event_type in {"PASSWORD_RESET_REQUIRED","NEW_LOGIN","MFA_CHANGED"}:return NotificationAudience.PERSONAL_SECURITY
        if event_type in {"TENANT_SESSION_TERMINATED","TENANT_FAILED_LOGIN_THRESHOLD"}:return NotificationAudience.TENANT_SECURITY
        if event_type in {"PLATFORM_ADMIN_CHANGED","PLATFORM_SECURITY_ALERT"}:return NotificationAudience.PLATFORM_SECURITY
        return NotificationAudience.OPERATIONAL


from core.classification_policy import ClassificationPolicy
class SensitiveNotificationPolicy:
    @classmethod
    def payload(cls,*,classification,title,message,reference_id='',url=''):
        return {'title':title,'message':ClassificationPolicy.notification_text(classification=classification,safe_text=message),'reference_id':reference_id,'url':url,'classification':str(classification or 'NORMAL')}
class SecurityNotificationAudience:
    PERSONAL_SECURITY='PERSONAL_SECURITY'; TENANT_SECURITY='TENANT_SECURITY'; PLATFORM_SECURITY='PLATFORM_SECURITY'
    @classmethod
    def validate(cls,*,audience,recipient,company):
        if audience==cls.PERSONAL_SECURITY:return True
        if audience==cls.TENANT_SECURITY:return getattr(recipient,'company_id',None)==getattr(company,'id',None)
        if audience==cls.PLATFORM_SECURITY:return getattr(recipient,'company_id',None) is None
        return False
