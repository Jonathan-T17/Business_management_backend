from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from companies.models import Company
from core.roles import Roles
from core.capabilities import Capabilities
from organizations.models import UserCapabilityGrant
from security.models import AuditLog, OTP
from security.services import SupportAccessService, generate_otp, verify_otp
from users.models import User

class OTPHardeningTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.user = User.objects.create_user(email="a@acme.test", full_name="A", password="test-pass-123", company=self.company, role=Roles.EMPLOYEE, is_active=True, email_verified=True)

    def test_otp_is_not_stored_in_plaintext(self):
        challenge, code = generate_otp(self.user)
        self.assertFalse(hasattr(challenge, "code"))
        self.assertNotEqual(challenge.code_digest, code)
        self.assertTrue(verify_otp(self.user, challenge_id=challenge.challenge_id, code=code))

    def test_otp_locks_after_failed_attempts(self):
        challenge, _ = generate_otp(self.user)
        for _ in range(challenge.max_attempts):
            verify_otp(self.user, challenge_id=challenge.challenge_id, code="000000")
        challenge.refresh_from_db()
        self.assertFalse(challenge.is_active)

class AuditImmutabilityTests(TestCase):
    def test_audit_log_cannot_be_updated_or_deleted(self):
        row = AuditLog.objects.create(action="TEST")
        row.description = "changed"
        with self.assertRaises(RuntimeError): row.save()
        with self.assertRaises(RuntimeError): row.delete()

class SupportAccessTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.agent = User.objects.create_superuser(email="support@test.com", full_name="Support", password="test-pass-123")
        self.approver = User.objects.create_superuser(email="platform@test.com", full_name="Platform", password="test-pass-123")
        # In Phase 1 these platform capabilities are supplied by the platform role policy.

    def test_sensitive_support_scope_is_rejected(self):
        with self.assertRaises(Exception):
            SupportAccessService.request(company=self.company, support_agent=self.agent, reason="ticket", scopes=["COMPENSATION"], expires_at=timezone.now()+timedelta(hours=1))
