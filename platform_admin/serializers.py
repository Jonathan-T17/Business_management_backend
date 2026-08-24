from rest_framework import serializers

from companies.models import Company
from notifications.models import EmailDeliveryLog
from users.models import User

from security.models import (
    ActiveSession,
    LoginHistory,
    FailedLoginAttempt,
    AuditLog,
)

from subscriptions.models import Subscription

from activity.models import ActivityLog


# ============================================================
# Company
# ============================================================

class PlatformCompanySerializer(
    serializers.ModelSerializer
):
    users_count = serializers.SerializerMethodField()
    branches_count = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()

    subscription_plan = serializers.SerializerMethodField()
    subscription_active = serializers.SerializerMethodField()

    class Meta:
        model = Company

        fields = (
            "id",
            "name",
            "slug",
            "email",
            "phone",
            "website",
            "address",
            "is_active",

            "users_count",
            "branches_count",
            "projects_count",

            "subscription_plan",
            "subscription_active",

            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_users_count(self, obj):
        return obj.users.filter(
            is_deleted=False
        ).count()

    def get_branches_count(self, obj):
        return obj.branches.count()

    def get_projects_count(self, obj):
        return obj.projects.count()

    def get_subscription_plan(self, obj):
        try:
            return obj.subscription.plan.name
        except Subscription.DoesNotExist:
            return None

    def get_subscription_active(self, obj):
        try:
            return obj.subscription.is_active
        except Subscription.DoesNotExist:
            return False


# ============================================================
# User
# ============================================================

class PlatformUserSerializer(
    serializers.ModelSerializer
):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    class Meta:
        model = User

        fields = (
            "id",
            "email",
            "full_name",
            "role",

            "company",
            "company_name",

            "branch",
            "branch_name",

            "is_active",
            "email_verified",
            "is_deleted",
            "mfa_enabled",

            "last_login_ip",
            "last_activity",

            "date_joined",
        )

        read_only_fields = fields


# ============================================================
# Active Session
# ============================================================

class PlatformActiveSessionSerializer(
    serializers.ModelSerializer
):
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = ActiveSession

        fields = (
            "id",

            "user",
            "user_email",

            "company",
            "company_name",

            "branch",

            "ip_address",
            "browser",
            "operating_system",
            "device",

            "last_activity",
            "expires_at",
            "terminated_at",

            "is_active",
        )

        read_only_fields = fields


# ============================================================
# Login History
# ============================================================

class PlatformLoginHistorySerializer(
    serializers.ModelSerializer
):
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = LoginHistory

        fields = (
            "id",

            "user",
            "user_email",

            "company",
            "company_name",

            "branch",

            "ip_address",
            "browser",
            "operating_system",
            "device",
            "location",

            "successful",
            "failure_reason",

            "created_at",
        )

        read_only_fields = fields


# ============================================================
# Failed Login
# ============================================================

class PlatformFailedLoginSerializer(
    serializers.ModelSerializer
):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = FailedLoginAttempt

        fields = (
            "id",
            "email",

            "company",
            "company_name",

            "ip_address",

            "attempts",
            "reason",
            "locked_until",
            "locked_by_system",
            "last_attempt_at",
        )

        read_only_fields = fields


# ============================================================
# Audit Log
# ============================================================

class PlatformAuditLogSerializer(
    serializers.ModelSerializer
):
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = AuditLog

        fields = (
            "id",

            "user",
            "user_email",

            "company",
            "company_name",

            "branch",

            "action",
            "severity",
            "actor_type",

            "object_type",
            "object_id",

            "description",

            "ip_address",
            "user_agent",

            "status",

            "created_at",
        )

        read_only_fields = fields


# ============================================================
# Subscription
# ============================================================

class PlatformSubscriptionSerializer(
    serializers.ModelSerializer
):
    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )

    max_users = serializers.IntegerField(
        source="plan.max_users",
        read_only=True,
    )

    max_projects = serializers.IntegerField(
        source="plan.max_projects",
        read_only=True,
    )

    users_used = serializers.SerializerMethodField()
    projects_used = serializers.SerializerMethodField()

    class Meta:
        model = Subscription

        fields = (
            "id",

            "company",
            "company_name",

            "plan",
            "plan_name",

            "max_users",
            "users_used",

            "max_projects",
            "projects_used",

            "is_active",

            "started_at",
            "expires_at",
        )

        read_only_fields = fields

    def get_users_used(self, obj):
        return obj.company.users.filter(
            is_deleted=False
        ).count()

    def get_projects_used(self, obj):
        return obj.company.projects.filter(
            is_active=True
        ).count()


# ============================================================
# Activity
# ============================================================

class PlatformActivitySerializer(
    serializers.ModelSerializer
):
    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    class Meta:
        model = ActivityLog

        fields = (
            "id",

            "company",
            "company_name",

            "project",
            "task",

            "user",
            "user_email",

            "action",
            "metadata",

            "created_at",
        )

        read_only_fields = fields





class PlatformEmailDeliverySerializer(
    serializers.ModelSerializer
):

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    user_email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = EmailDeliveryLog

        fields = "__all__"

        read_only_fields = fields