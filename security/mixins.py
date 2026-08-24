from security.services import create_audit_log


class AuditMixin:

    audit_action = None

    def log_action(self, request, obj):

        create_audit_log(
            user=request.user,
            action=self.audit_action,
            request=request,
            object_id=obj.id,
        )

    def perform_create(self, serializer):

        obj = serializer.save()

        self.log_action(
            self.request,
            obj,
        )

    def perform_update(self, serializer):

        obj = serializer.save()

        self.log_action(
            self.request,
            obj,
        )

    def perform_destroy(self, instance):

        self.log_action(
            self.request,
            instance,
        )

        instance.delete()