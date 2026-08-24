from datetime import timedelta

from django.utils import timezone

from companies.models import Company
from users.models import User

from projects.models import Project
from tasks.models import Task
from reports.models import Report

from subscriptions.models import Subscription

from notifications.models import EmailDeliveryLog

from security.models import (
    ActiveSession,
    FailedLoginAttempt,
    AuditLog,
)


class PlatformDashboardService:

    @staticmethod
    def build():

        now = timezone.now()

        last_24_hours = (
            now
            - timedelta(hours=24)
        )

        month_start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        expiring_limit = (
            now
            + timedelta(days=7)
        )

        companies = Company.objects.all()

        users = User.objects.filter(
            is_deleted=False
        )

        projects = Project.objects.all()

        tasks = Task.objects.all()

        subscriptions = (
            Subscription.objects
            .select_related(
                "company",
                "plan",
            )
        )

        active_sessions = (
            ActiveSession.objects.filter(
                is_active=True
            )
        )

        failed_logins_24h = (
            FailedLoginAttempt.objects.filter(
                last_attempt_at__gte=
                    last_24_hours
            )
        )

        locked_records = (
            FailedLoginAttempt.objects.filter(
                locked_until__gt=now
            )
        )

        critical_events = (
            AuditLog.objects.filter(
                severity="CRITICAL",
                created_at__gte=
                    last_24_hours,
            )
        )

        emails_last_24h = (
            EmailDeliveryLog.objects.filter(
                created_at__gte=
                    last_24_hours
            )
        )

        active_subscriptions = (
            subscriptions.filter(
                is_active=True
            )
        )

        expired_subscriptions = (
            subscriptions.filter(
                expires_at__lt=now
            )
        )

        expiring_subscriptions = (
            subscriptions.filter(
                is_active=True,
                expires_at__gte=now,
                expires_at__lte=
                    expiring_limit,
            )
        )

        return {
            "companies": {
                "total":
                    companies.count(),

                "active":
                    companies.filter(
                        is_active=True
                    ).count(),

                "new_this_month":
                    companies.filter(
                        created_at__gte=
                            month_start
                    ).count(),
            },

            "users": {
                "total":
                    users.count(),

                "active":
                    users.filter(
                        is_active=True
                    ).count(),

                "new_this_month":
                    users.filter(
                        date_joined__gte=
                            month_start
                    ).count(),
            },

            "projects": {
                "total":
                    projects.count(),

                "active":
                    projects.filter(
                        is_active=True
                    ).count(),
            },

            "tasks": {
                "total":
                    tasks.count(),

                "active":
                    tasks.filter(
                        is_active=True
                    ).count(),

                "completed":
                    tasks.filter(
                        status="done"
                    ).count(),
            },

            "reports": {
                "total":
                    Report.objects.count(),

                "last_24h":
                    Report.objects.filter(
                        created_at__gte=
                            last_24_hours
                    ).count(),
            },

            "communications": {
                "sent_24h":
                    emails_last_24h.filter(
                        status="SENT"
                    ).count(),

                "failed_24h":
                    emails_last_24h.filter(
                        status="FAILED"
                    ).count(),

                "pending":
                    EmailDeliveryLog.objects.filter(
                        status="PENDING"
                    ).count(),
            },
        
            # Success rate percentage
            "success_rate": round(
                (
                    emails_last_24h.filter(status="SENT").count()
                    / max(emails_last_24h.count(), 1)
                ) * 100,
                2,
            ),
        
            # Failure rate percentage
            "failure_rate": round(
                (
                    emails_last_24h.filter(status="FAILED").count()
                    / max(emails_last_24h.count(), 1)
                ) * 100,
                2,
            ),
        
            # Trend comparison (last 7 days vs last 24h)
            "trend": {
                "last_7_days_sent": EmailDeliveryLog.objects.filter(
                    created_at__gte=now - timedelta(days=7),
                    status="SENT"
                ).count(),
                "last_7_days_failed": EmailDeliveryLog.objects.filter(
                    created_at__gte=now - timedelta(days=7),
                    status="FAILED"
                ).count(),
            },
            

            "security": {
                "active_sessions":
                    active_sessions.count(),

                "failed_logins_24h":
                    failed_logins_24h.count(),

                "locked_records":
                    locked_records.count(),

                "critical_events_24h":
                    critical_events.count(),
            },

            "subscriptions": {
                "active":
                    active_subscriptions.count(),

                "expired":
                    expired_subscriptions.count(),

                "expiring_soon":
                    expiring_subscriptions.count(),
            },
        }