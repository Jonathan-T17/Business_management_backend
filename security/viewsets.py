from rest_framework.viewsets import ModelViewSet
from django.db import transaction

from security.mixins import AuditMixin
from core.tenant import TenantService
from security.object_permissions import CompanyObjectPermission
from security.services import create_audit_log


class SecureModelViewSet(AuditMixin, ModelViewSet):

    audit_action = None

    def get_queryset(self):
        user = self.request.user
        model = self.queryset.model.__name__

        services = {
            "User": TenantService.users,
            "Company": TenantService.companies,
            "Branch": TenantService.branches,
            "Project": TenantService.projects,
            "ProjectMembership": TenantService.project_memberships,
            "Task": TenantService.tasks,
            "Report": TenantService.reports,
            "ReportComment": TenantService.comments,
            "Notification": TenantService.notifications,
            "ActivityLog": TenantService.activity,
            "CompanyInvite": TenantService.invites,
            "Subscription": TenantService.subscriptions,
            "AnalyticsSnapshot": TenantService.analytics_snapshots,
            "AIInsight": TenantService.ai_insights,
        }

        service = services.get(model)

        if service:
            return service(user)

        return TenantService.filter(
            self.queryset,
            user,
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            obj = serializer.save()
            CompanyObjectPermission.validate(self.request.user, obj)
            create_audit_log(
                user=self.request.user,
                action=self.audit_action or "CREATE",
                request=self.request,
                obj=obj,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            obj = serializer.save()
            CompanyObjectPermission.validate(self.request.user, obj)
            create_audit_log(
                user=self.request.user,
                action=self.audit_action or "UPDATE",
                request=self.request,
                obj=obj,
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            CompanyObjectPermission.validate(self.request.user, instance)
            create_audit_log(
                user=self.request.user,
                action=self.audit_action or "DELETE",
                request=self.request,
                obj=instance,
            )

            if hasattr(instance, "is_active"):
                instance.is_active = False
                instance.save(update_fields=["is_active"])
            else:
                instance.delete()



# from rest_framework.viewsets import ModelViewSet
# from rest_framework.exceptions import PermissionDenied
# from security.mixins import AuditMixin
# from core.tenant import TenantService
# from security.object_permissions import CompanyObjectPermission
# from security.services import create_audit_log


# class SecureModelViewSet(AuditMixin, ModelViewSet):
#     """
#     Base ViewSet for all secured resources.

#     Child classes should define:
#     - queryset
#     - serializer_class
#     - permission_classes
#     - audit_action (string describing the action)
#     """

#     audit_action = None

#     # ---------------------------
#     # Tenant Filtering
#     # ---------------------------
#     def get_queryset(self):
#         user = self.request.user
#         model = self.queryset.model.__name__

#         # Delegate to TenantService for model-specific filtering
#         if model == "User":
#             return TenantService.users(user)
#         if model == "Company":
#             return TenantService.companies(user)
#         if model == "Branch":
#             return TenantService.branches(user)
#         if model == "Project":
#             return TenantService.projects(user)
#         if model == "ProjectMembership":
#             return TenantService.project_memberships(user)
#         if model == "Task":
#             return TenantService.tasks(user)
#         if model == "Report":
#             return TenantService.reports(user)
#         if model == "ReportComment":
#             return TenantService.comments(user)
#         if model == "Notification":
#             return TenantService.notifications(user)
#         if model == "ActivityLog":
#             return TenantService.activity(user)

#         # fallback for simple models with company/branch fields
#         return TenantService.filter(super().get_queryset(), user)

#     # ---------------------------
#     # Create
#     # ---------------------------
#     def perform_create(self, serializer):
#         obj = serializer.save()
#         CompanyObjectPermission.validate(self.request.user, obj)
#         create_audit_log(
#             user=self.request.user,
#             action=self.audit_action or "CREATE",
#             request=self.request,
#             obj=obj,
#         )

#     # ---------------------------
#     # Update
#     # ---------------------------
#     def perform_update(self, serializer):
#         obj = serializer.save()
#         CompanyObjectPermission.validate(self.request.user, obj)
#         create_audit_log(
#             user=self.request.user,
#             action=self.audit_action or "UPDATE",
#             request=self.request,
#             obj=obj,
#         )

#     # ---------------------------
#     # Soft Delete
#     # ---------------------------
#     def perform_destroy(self, instance):
#         CompanyObjectPermission.validate(self.request.user, instance)
#         create_audit_log(
#             user=self.request.user,
#             action=self.audit_action or "DELETE",
#             request=self.request,
#             obj=instance,
#         )
#         # Soft delete support: mark inactive instead of hard delete
#         if hasattr(instance, "is_active"):
#             instance.is_active = False
#             instance.save()
#         else:
#             instance.delete()
