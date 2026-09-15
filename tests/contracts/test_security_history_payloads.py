from companies.models import Company
from users.models import User
from security.models import AuditLog, LoginHistory
from platform_admin.serializers import PlatformAuditSummarySerializer, PlatformLoginHistorySerializer


def test_login_history_identifies_actor_and_company_without_sensitive_payload():
    user = User(email="operator@example.test")
    company = Company(name="Example company")
    event = LoginHistory(user=user, company=company, successful=True)
    data = PlatformLoginHistorySerializer(event).data
    assert data["user_email"] == user.email
    assert data["company_name"] == company.name
    assert "user_agent" not in data


def test_login_history_handles_platform_and_deleted_users():
    data = PlatformLoginHistorySerializer(LoginHistory()).data
    assert data["user_email"] is None
    assert data["company_name"] is None


def test_platform_audit_does_not_expose_company_business_content():
    event = AuditLog(description="Confidential form content", metadata={"salary": 1000})
    data = PlatformAuditSummarySerializer(event).data
    assert "description" not in data
    assert "metadata" not in data
