from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from companies.models import Company
from notifications.models import EmailDeliveryLog
from users.models import User

from activity.models import ActivityLog

from subscriptions.models import (
    Subscription,
    Plan,
)

from security.models import (
    ActiveSession,
    LoginHistory,
    FailedLoginAttempt,
    AuditLog,
)

from security.services import (
    create_audit_log,
)

from .permissions import (
    IsPlatformSuperUser,
)

from .serializers import (
    PlatformCompanySerializer,
    PlatformUserSerializer,
    PlatformActiveSessionSerializer,
    PlatformLoginHistorySerializer,
    PlatformFailedLoginSerializer,
    PlatformAuditLogSerializer,
    PlatformSubscriptionSerializer,
    PlatformActivitySerializer,
    PlatformEmailDeliverySerializer,
)

from .services import (
    PlatformDashboardService,
)

from .health import (
    get_platform_health,
)


# ============================================================
# Dashboard
# ============================================================

class PlatformDashboardView(APIView):

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get(self, request):

        data = (
            PlatformDashboardService
            .build()
        )

        recent_audit = (
            AuditLog.objects
            .select_related(
                "user",
                "company",
                "branch",
            )
            .order_by(
                "-created_at"
            )[:10]
        )

        recent_companies = (
            Company.objects
            .order_by(
                "-created_at"
            )[:5]
        )

        data[
            "recent_audit_events"
        ] = (
            PlatformAuditLogSerializer(
                recent_audit,
                many=True,
            ).data
        )

        data[
            "recent_companies"
        ] = (
            PlatformCompanySerializer(
                recent_companies,
                many=True,
            ).data
        )

        data["system_health"] = (
            get_platform_health()
        )

        return Response(data)


# ============================================================
# Companies
# ============================================================

class PlatformCompanyViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformCompanySerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            Company.objects
            .select_related(
                "created_by"
            )
            .prefetch_related(
                "branches",
                "users",
                "projects",
            )
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        status_filter = (
            self.request
            .query_params
            .get("status")
        )

        if search:
            queryset = queryset.filter(
                name__icontains=search
            )

        if status_filter == "active":
            queryset = queryset.filter(
                is_active=True
            )

        elif status_filter == "inactive":
            queryset = queryset.filter(
                is_active=False
            )

        return queryset


    @action(
        detail=True,
        methods=["post"],
        url_path="deactivate",
    )
    def deactivate(
        self,
        request,
        pk=None,
    ):

        company = self.get_object()

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        if not reason:
            raise ValidationError({
                "reason":
                    "A reason is required."
            })

        company.is_active = False

        company.save(
            update_fields=[
                "is_active"
            ]
        )

        create_audit_log(
            user=request.user,
            company=company,
            request=request,
            action="UPDATE",
            description=(
                f"Platform administrator "
                f"deactivated company "
                f"{company.name}. "
                f"Reason: {reason}"
            ),
            obj=company,
        )

        return Response({
            "message":
                "Company deactivated."
        })


    @action(
        detail=True,
        methods=["post"],
        url_path="activate",
    )
    def activate(
        self,
        request,
        pk=None,
    ):

        company = self.get_object()

        company.is_active = True

        company.save(
            update_fields=[
                "is_active"
            ]
        )

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        create_audit_log(
            user=request.user,
            company=company,
            request=request,
            action="UPDATE",
            description=(
                f"Platform administrator "
                f"activated company "
                f"{company.name}."
                + (
                    f" Reason: {reason}"
                    if reason
                    else ""
                )
            ),
            obj=company,
        )

        return Response({
            "message":
                "Company activated."
        })


# ============================================================
# Users
# ============================================================

class PlatformUserViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformUserSerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            User.objects
            .select_related(
                "company",
                "branch",
            )
            .order_by(
                "-date_joined"
            )
        )

        company_id = (
            self.request
            .query_params
            .get("company")
        )

        role = (
            self.request
            .query_params
            .get("role")
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        if company_id:
            queryset = queryset.filter(
                company_id=company_id
            )

        if role:
            queryset = queryset.filter(
                role=role
            )

        if search:
            queryset = queryset.filter(
                email__icontains=search
            ) | queryset.filter(
                full_name__icontains=search
            )

        return queryset.distinct()


    @action(
        detail=True,
        methods=["post"],
        url_path="terminate-sessions",
    )
    def terminate_sessions(
        self,
        request,
        pk=None,
    ):

        target_user = self.get_object()

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        if not reason:
            raise ValidationError({
                "reason":
                    "A reason is required."
            })

        sessions = (
            ActiveSession.objects.filter(
                user=target_user,
                is_active=True,
            )
        )

        count = sessions.update(
            is_active=False,
            terminated_at=
                timezone.now(),
        )

        create_audit_log(
            user=request.user,
            company=
                target_user.company,
            branch=
                target_user.branch,
            request=request,
            action="SECURITY",
            description=(
                f"Platform administrator "
                f"terminated {count} "
                f"session(s) for "
                f"{target_user.email}. "
                f"Reason: {reason}"
            ),
            obj=target_user,
        )

        return Response({
            "message":
                "User sessions terminated.",
            "terminated_sessions":
                count,
        })


# ============================================================
# Active Sessions
# ============================================================

class PlatformActiveSessionViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformActiveSessionSerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            ActiveSession.objects
            .select_related(
                "user",
                "company",
                "branch",
            )
            .order_by(
                "-last_activity"
            )
        )

        active = (
            self.request
            .query_params
            .get("active")
        )

        company = (
            self.request
            .query_params
            .get("company")
        )

        if active == "true":
            queryset = queryset.filter(
                is_active=True
            )

        elif active == "false":
            queryset = queryset.filter(
                is_active=False
            )

        if company:
            queryset = queryset.filter(
                company_id=company
            )

        return queryset


    @action(
        detail=True,
        methods=["post"],
        url_path="terminate",
    )
    def terminate(
        self,
        request,
        pk=None,
    ):

        session = self.get_object()

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        if not reason:
            raise ValidationError({
                "reason":
                    "A reason is required."
            })

        if not session.is_active:
            return Response(
                {
                    "message":
                        "Session is already inactive."
                }
            )

        session.is_active = False
        session.terminated_at = (
            timezone.now()
        )

        session.save(
            update_fields=[
                "is_active",
                "terminated_at",
            ]
        )

        create_audit_log(
            user=request.user,
            company=session.company,
            branch=session.branch,
            request=request,
            action="SECURITY",
            description=(
                f"Platform administrator "
                f"terminated session for "
                f"{session.user.email}. "
                f"Reason: {reason}"
            ),
            obj=session,
        )

        return Response({
            "message":
                "Session terminated."
        })


# ============================================================
# Login History
# ============================================================

class PlatformLoginHistoryViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformLoginHistorySerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            LoginHistory.objects
            .select_related(
                "user",
                "company",
                "branch",
            )
            .order_by(
                "-created_at"
            )
        )

        successful = (
            self.request
            .query_params
            .get("successful")
        )

        company = (
            self.request
            .query_params
            .get("company")
        )

        if successful == "true":
            queryset = queryset.filter(
                successful=True
            )

        elif successful == "false":
            queryset = queryset.filter(
                successful=False
            )

        if company:
            queryset = queryset.filter(
                company_id=company
            )

        return queryset


# ============================================================
# Failed Login Attempts
# ============================================================

class PlatformFailedLoginViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformFailedLoginSerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):
        return (
            FailedLoginAttempt.objects
            .select_related(
                "company"
            )
            .order_by(
                "-last_attempt_at"
            )
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="unlock",
    )
    def unlock(
        self,
        request,
        pk=None,
    ):

        attempt = self.get_object()

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        if not reason:
            raise ValidationError({
                "reason":
                    "A reason is required."
            })

        attempt.attempts = 0
        attempt.locked_until = None

        attempt.save(
            update_fields=[
                "attempts",
                "locked_until",
            ]
        )

        create_audit_log(
            user=request.user,
            company=attempt.company,
            request=request,
            action="SECURITY",
            description=(
                f"Platform administrator "
                f"cleared login lock for "
                f"{attempt.email} "
                f"from {attempt.ip_address}. "
                f"Reason: {reason}"
            ),
            obj=attempt,
        )

        return Response({
            "message":
                "Login lock cleared."
        })


# ============================================================
# Audit Logs
# ============================================================

class PlatformAuditLogViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformAuditLogSerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            AuditLog.objects
            .select_related(
                "user",
                "company",
                "branch",
            )
            .order_by(
                "-created_at"
            )
        )

        company = (
            self.request
            .query_params
            .get("company")
        )

        user = (
            self.request
            .query_params
            .get("user")
        )

        action_name = (
            self.request
            .query_params
            .get("action")
        )

        severity = (
            self.request
            .query_params
            .get("severity")
        )

        status_name = (
            self.request
            .query_params
            .get("status")
        )

        object_type = (
            self.request
            .query_params
            .get("object_type")
        )

        if company:
            queryset = queryset.filter(
                company_id=company
            )

        if user:
            queryset = queryset.filter(
                user_id=user
            )

        if action_name:
            queryset = queryset.filter(
                action=action_name
            )

        if severity:
            queryset = queryset.filter(
                severity=severity
            )

        if status_name:
            queryset = queryset.filter(
                status=status_name
            )

        if object_type:
            queryset = queryset.filter(
                object_type=
                    object_type
            )

        return queryset


# ============================================================
# Subscriptions
# ============================================================

class PlatformSubscriptionViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformSubscriptionSerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):
        return (
            Subscription.objects
            .select_related(
                "company",
                "plan",
            )
            .order_by(
                "-started_at"
            )
        )


    @action(
        detail=True,
        methods=["post"],
        url_path="change-plan",
    )
    def change_plan(
        self,
        request,
        pk=None,
    ):

        subscription = (
            self.get_object()
        )

        plan_id = (
            request.data
            .get("plan_id")
        )

        reason = (
            request.data
            .get("reason", "")
            .strip()
        )

        if not reason:
            raise ValidationError({
                "reason":
                    "A reason is required."
            })

        if not plan_id:
            raise ValidationError({
                "plan_id":
                    "Plan is required."
            })

        try:
            plan = Plan.objects.get(
                id=plan_id
            )
        except Plan.DoesNotExist:
            raise ValidationError({
                "plan_id":
                    "Invalid plan."
            })

        old_plan = (
            subscription.plan
        )

        subscription.plan = plan

        subscription.save(
            update_fields=[
                "plan"
            ]
        )

        create_audit_log(
            user=request.user,
            company=
                subscription.company,
            request=request,
            action="UPDATE",
            description=(
                f"Platform administrator "
                f"changed subscription "
                f"from {old_plan.name} "
                f"to {plan.name}. "
                f"Reason: {reason}"
            ),
            obj=subscription,
        )

        serializer = (
            self.get_serializer(
                subscription
            )
        )

        return Response(
            serializer.data
        )


# ============================================================
# Global Activity
# ============================================================

class PlatformActivityViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        PlatformActivitySerializer
    )

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get_queryset(self):

        queryset = (
            ActivityLog.objects
            .select_related(
                "company",
                "project",
                "task",
                "user",
            )
            .order_by(
                "-created_at"
            )
        )

        company = (
            self.request
            .query_params
            .get("company")
        )

        if company:
            queryset = queryset.filter(
                company_id=company
            )

        return queryset


# ============================================================
# Health
# ============================================================

class PlatformHealthView(APIView):

    permission_classes = [
        IsPlatformSuperUser,
    ]

    def get(self, request):

        return Response(
            get_platform_health(),
            status=
                status.HTTP_200_OK,
        )



class PlatformEmailDeliveryViewSet(
    viewsets.ReadOnlyModelViewSet
):
    serializer_class = (
        PlatformEmailDeliverySerializer
    )

    permission_classes = [
        IsPlatformSuperUser
    ]

    def get_queryset(self):

        queryset = (
            EmailDeliveryLog.objects
            .select_related(
                "company",
                "user",
            )
        )

        status_name = (
            self.request
            .query_params
            .get("status")
        )

        company = (
            self.request
            .query_params
            .get("company")
        )

        if status_name:
            queryset = queryset.filter(
                status=status_name
            )

        if company:
            queryset = queryset.filter(
                company_id=company
            )

        return queryset