from rest_framework import serializers
from companies.models import Company
from users.models import User
from security.models import ActiveSession, AuditLog, FailedLoginAttempt, LoginHistory, SupportAccessSession

class PlatformCompanySummarySerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(source="users.count", read_only=True)
    branches_count = serializers.IntegerField(source="branches.count", read_only=True)
    projects_count = serializers.IntegerField(source="projects.count", read_only=True)
    subscription_plan = serializers.CharField(source="subscription.plan.name", read_only=True, default=None)
    subscription_active = serializers.BooleanField(source="subscription.is_valid", read_only=True, default=False)
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from .permissions import IsPlatformSuperUser
        request = self.context.get("request")
        if not request or not IsPlatformSuperUser().has_permission(request, None):
            return []
        return ["DEACTIVATE" if obj.is_active else "REACTIVATE"]

    class Meta:
        model = Company
        fields = ("id","name","slug","is_active","users_count","created_at","updated_at",
                  "email","phone","website","address","branches_count","projects_count",
                  "subscription_plan","subscription_active","allowed_actions")
        read_only_fields = fields

class PlatformUserSummarySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = User
        fields = ("id","email","full_name","role","company","company_name","is_active","email_verified","account_state","date_joined")
        read_only_fields = fields

class PlatformSessionSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, obj) -> list[str]:
        from .permissions import IsPlatformSuperUser
        request = self.context.get("request")
        return ["TERMINATE"] if request and obj.is_active and IsPlatformSuperUser().has_permission(request, None) else []

    user_email = serializers.CharField(source="user.email", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = ActiveSession
        fields = ("id","user_email","company_name","ip_address","browser","operating_system","device","last_activity","expires_at","terminated_at","termination_reason","is_active","allowed_actions")
        read_only_fields = fields

class PlatformAuditSummarySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = AuditLog
        fields = ("id","company_name","action","severity","actor_type","object_type","status","created_at")
        read_only_fields = fields

class PlatformFailedLoginSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    class Meta:
        model = FailedLoginAttempt
        fields = ("id","email_hint","company_name","ip_address","attempts","locked_until","last_attempt_at")
        read_only_fields = fields

class SupportAccessSessionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    agent_name = serializers.CharField(source="support_agent.full_name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.full_name", read_only=True)
    class Meta:
        model = SupportAccessSession
        fields = ("id","company","company_name","support_agent","agent_name","ticket","reason","scopes","status","requested_at","approved_by_name","approved_at","starts_at","expires_at","ended_at")
        read_only_fields = fields


PlatformCompanySerializer = PlatformCompanySummarySerializer
PlatformUserSerializer = PlatformUserSummarySerializer
PlatformActiveSessionSerializer = PlatformSessionSerializer
PlatformAuditLogSerializer = PlatformAuditSummarySerializer


class PlatformLoginHistorySerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True, allow_null=True)
    company_name = serializers.CharField(source="company.name", read_only=True, allow_null=True)

    class Meta:
        model = LoginHistory
        fields = ("id", "company", "company_name", "user", "user_email", "ip_address", "browser", "operating_system", "device", "successful", "created_at")
        read_only_fields = fields


class PlatformPlanSerializer(serializers.ModelSerializer):
    class Meta:
        from subscriptions.models import Plan
        model = Plan
        fields = ("id", "name", "max_users", "max_projects", "max_branches", "price_monthly", "is_active")
        read_only_fields = fields


class PlatformPlanChangeSerializer(serializers.Serializer):
    from subscriptions.models import Plan
    plan_id = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.filter(is_active=True))
    reason = serializers.CharField(max_length=1000, trim_whitespace=True)


class PlatformSubscriptionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    max_users = serializers.IntegerField(source="plan.max_users", read_only=True)
    max_projects = serializers.IntegerField(source="plan.max_projects", read_only=True)
    users_used = serializers.IntegerField(read_only=True)
    projects_used = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        from subscriptions.models import Subscription
        model = Subscription
        fields = ("id", "company", "company_name", "plan", "plan_name", "max_users", "max_projects", "users_used", "projects_used", "is_active", "is_valid", "started_at", "expires_at")
        read_only_fields = fields


class PlatformActivitySerializer(serializers.ModelSerializer):
    class Meta:
        from activity.models import ActivityLog
        model = ActivityLog
        fields = ("id", "company", "action", "created_at")
        read_only_fields = fields


class PlatformEmailDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        from notifications.models import EmailDeliveryLog
        model = EmailDeliveryLog
        fields = ("id", "company", "status", "created_at")
        read_only_fields = fields





# from rest_framework import serializers

# from companies.models import Company
# from notifications.models import EmailDeliveryLog
# from users.models import User

# from security.models import (
#     ActiveSession,
#     LoginHistory,
#     FailedLoginAttempt,
#     AuditLog,
# )

# from subscriptions.models import Subscription

# from activity.models import ActivityLog
# from core.action_policy import actions_for


# # ============================================================
# # Company
# # ============================================================

# class PlatformCompanySerializer(
#     serializers.ModelSerializer
# ):
#     users_count = serializers.SerializerMethodField()
#     branches_count = serializers.SerializerMethodField()
#     projects_count = serializers.SerializerMethodField()

#     subscription_plan = serializers.SerializerMethodField()
#     subscription_active = serializers.SerializerMethodField()
#     allowed_actions = serializers.SerializerMethodField()

#     class Meta:
#         model = Company

#         fields = (
#             "id",
#             "name",
#             "slug",
#             "email",
#             "phone",
#             "website",
#             "address",
#             "is_active",

#             "users_count",
#             "branches_count",
#             "projects_count",

#             "subscription_plan",
#             "subscription_active",

#             "created_at",
#             "updated_at",
#             "allowed_actions",
#         )

#         read_only_fields = fields

#     def get_users_count(self, obj):
#         return obj.users.filter(
#             is_deleted=False
#         ).count()

#     def get_branches_count(self, obj):
#         return obj.branches.count()

#     def get_projects_count(self, obj):
#         return obj.projects.count()

#     def get_subscription_plan(self, obj):
#         try:
#             return obj.subscription.plan.name
#         except Subscription.DoesNotExist:
#             return None

#     def get_subscription_active(self, obj):
#         try:
#             return obj.subscription.is_active
#         except Subscription.DoesNotExist:
#             return False

#     def get_allowed_actions(self, obj) -> list[str]:
#         request = self.context.get("request")
#         return actions_for(request.user, target=obj) if request else []


# # ============================================================
# # User
# # ============================================================

# class PlatformUserSerializer(
#     serializers.ModelSerializer
# ):
#     allowed_actions = serializers.SerializerMethodField()
#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     branch_name = serializers.CharField(
#         source="branch.name",
#         read_only=True,
#     )

#     class Meta:
#         model = User

#         fields = (
#             "id",
#             "email",
#             "full_name",
#             "role",

#             "company",
#             "company_name",

#             "branch",
#             "branch_name",

#             "is_active",
#             "email_verified",
#             "is_deleted",
#             "mfa_enabled",

#             "last_login_ip",
#             "last_activity",

#             "date_joined",
#             "allowed_actions",
#         )

#         read_only_fields = fields

#     def get_allowed_actions(self, obj) -> list[str]:
#         request = self.context.get("request")
#         return actions_for(request.user if request else obj, target=obj)


# # ============================================================
# # Active Session
# # ============================================================

# class PlatformActiveSessionSerializer(
#     serializers.ModelSerializer
# ):
#     user_email = serializers.CharField(
#         source="user.email",
#         read_only=True,
#     )

#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     class Meta:
#         model = ActiveSession

#         fields = (
#             "id",

#             "user",
#             "user_email",

#             "company",
#             "company_name",

#             "branch",

#             "ip_address",
#             "browser",
#             "operating_system",
#             "device",

#             "last_activity",
#             "expires_at",
#             "terminated_at",

#             "is_active",
#         )

#         read_only_fields = fields


# # ============================================================
# # Login History
# # ============================================================

# class PlatformLoginHistorySerializer(
#     serializers.ModelSerializer
# ):
#     user_email = serializers.CharField(
#         source="user.email",
#         read_only=True,
#     )

#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     class Meta:
#         model = LoginHistory

#         fields = (
#             "id",

#             "user",
#             "user_email",

#             "company",
#             "company_name",

#             "branch",

#             "ip_address",
#             "browser",
#             "operating_system",
#             "device",
#             "location",

#             "successful",
#             "failure_reason",

#             "created_at",
#         )

#         read_only_fields = fields


# # ============================================================
# # Failed Login
# # ============================================================

# class PlatformFailedLoginSerializer(
#     serializers.ModelSerializer
# ):
#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     class Meta:
#         model = FailedLoginAttempt

#         fields = (
#             "id",
#             "email",

#             "company",
#             "company_name",

#             "ip_address",

#             "attempts",
#             "reason",
#             "locked_until",
#             "locked_by_system",
#             "last_attempt_at",
#         )

#         read_only_fields = fields


# # ============================================================
# # Audit Log
# # ============================================================

# class PlatformAuditLogSerializer(
#     serializers.ModelSerializer
# ):
#     user_email = serializers.CharField(
#         source="user.email",
#         read_only=True,
#     )

#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     class Meta:
#         model = AuditLog

#         fields = (
#             "id",

#             "user",
#             "user_email",

#             "company",
#             "company_name",

#             "branch",

#             "action",
#             "severity",
#             "actor_type",

#             "object_type",
#             "object_id",

#             "description",

#             "ip_address",
#             "user_agent",

#             "status",

#             "created_at",
#         )

#         read_only_fields = fields


# # ============================================================
# # Subscription
# # ============================================================

# class PlatformSubscriptionSerializer(
#     serializers.ModelSerializer
# ):
#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     plan_name = serializers.CharField(
#         source="plan.name",
#         read_only=True,
#     )

#     max_users = serializers.IntegerField(
#         source="plan.max_users",
#         read_only=True,
#     )

#     max_projects = serializers.IntegerField(
#         source="plan.max_projects",
#         read_only=True,
#     )

#     users_used = serializers.SerializerMethodField()
#     projects_used = serializers.SerializerMethodField()

#     class Meta:
#         model = Subscription

#         fields = (
#             "id",

#             "company",
#             "company_name",

#             "plan",
#             "plan_name",

#             "max_users",
#             "users_used",

#             "max_projects",
#             "projects_used",

#             "is_active",

#             "started_at",
#             "expires_at",
#         )

#         read_only_fields = fields

#     def get_users_used(self, obj):
#         return obj.company.users.filter(
#             is_deleted=False
#         ).count()

#     def get_projects_used(self, obj):
#         return obj.company.projects.filter(
#             is_active=True
#         ).count()


# # ============================================================
# # Activity
# # ============================================================

# class PlatformActivitySerializer(
#     serializers.ModelSerializer
# ):
#     user_email = serializers.CharField(
#         source="user.email",
#         read_only=True,
#     )

#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     class Meta:
#         model = ActivityLog

#         fields = (
#             "id",

#             "company",
#             "company_name",

#             "project",
#             "task",

#             "user",
#             "user_email",

#             "action",
#             "metadata",

#             "created_at",
#         )

#         read_only_fields = fields





# class PlatformEmailDeliverySerializer(
#     serializers.ModelSerializer
# ):

#     company_name = serializers.CharField(
#         source="company.name",
#         read_only=True,
#     )

#     user_email = serializers.CharField(
#         source="user.email",
#         read_only=True,
#     )

#     class Meta:
#         model = EmailDeliveryLog

#         fields = "__all__"

#         read_only_fields = fields

#     def get_allowed_actions(self, obj) -> list[str]:
#         request = self.context.get("request")
#         return actions_for(request.user, target=obj) if request else []
