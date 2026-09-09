from django.test import TestCase

from companies.models import Company
from notifications.models import Notification
from notifications.services import create_notification
from users.models import User


class SecurityNotificationTests(TestCase):

	def setUp(self):
		self.company = Company.objects.create(name="Example Company")
		self.superuser = User.objects.create_user(
			email="platform@example.com",
			full_name="Platform User",
			password="Strong-test-password-123!",
			role="SUPERUSER",
			is_superuser=True,
			is_active=True,
		)
		self.admin = User.objects.create_user(
			email="admin@example.com",
			full_name="Company Admin",
			password="Strong-test-password-123!",
			role="ADMIN",
			company=self.company,
			is_active=True,
		)

	def test_security_notification_is_sent_only_to_superuser(self):
		create_notification(
			recipient=self.admin,
			company=self.company,
			notification_type="OTP_FAILED",
			title="OTP Failed",
			message="An OTP failed.",
		)

		self.assertTrue(
			Notification.objects.filter(
				recipient=self.superuser,
				notification_type="OTP_FAILED",
			).exists()
		)
		self.assertFalse(
			Notification.objects.filter(
				recipient=self.admin,
				notification_type="OTP_FAILED",
			).exists()
		)

	def test_regular_notifications_stay_with_recipient(self):
		create_notification(
			recipient=self.admin,
			company=self.company,
			notification_type="SYSTEM",
			title="System update",
			message="An update is available.",
		)

		self.assertTrue(
			Notification.objects.filter(
				recipient=self.admin,
				notification_type="SYSTEM",
			).exists()
		)
		self.assertFalse(
			Notification.objects.filter(
				recipient=self.superuser,
				notification_type="SYSTEM",
			).exists()
		)
