from django.db import transaction
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from core.roles import Roles
from core.visibility import VisibilityService
from security.services import create_audit_log

from workflows.models import (
    WorkflowDefinition,
    WorkflowInstance,
)

from .models import (
    FormTemplate,
    FormSubmission,
)

from .serializers import (
    FormTemplateSerializer,
    FormSubmissionSerializer,
)

from .permissions import (
    CanManageFormTemplates,
    CanUseForms,
)

from .services import (
    FormSubmissionService,
)


# ============================================================
# Form Templates
# ============================================================

class FormTemplateViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FormTemplateSerializer
    )

    def get_permissions(self):

        if self.action in (
            "list",
            "retrieve",
        ):
            return [
                IsAuthenticated(),
                CanUseForms(),
            ]

        return [
            IsAuthenticated(),
            CanManageFormTemplates(),
        ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FormTemplate.objects
            .select_related(
                "company",
                "branch",
                "department",
                "team",
                "workflow",
                "created_by",
            )
            .prefetch_related(
                "fields"
            )
        )

        if user.role == Roles.SUPERUSER:
            return queryset

        if not user.company_id:
            return queryset.none()

        queryset = queryset.filter(
            company=user.company,
        )

        # Employees/managers only see templates
        # applicable to their organizational scope.
        if user.role in (
            Roles.MANAGER,
            Roles.EMPLOYEE,
        ):

            profile = getattr(
                user,
                "employee_profile",
                None,
            )

            branch_id = getattr(
                user,
                "branch_id",
                None,
            )

            department_id = (
                getattr(
                    profile,
                    "department_id",
                    None,
                )
            )

            team_id = (
                getattr(
                    profile,
                    "team_id",
                    None,
                )
            )

            queryset = queryset.filter(
                Q(branch__isnull=True)
                |
                Q(branch_id=branch_id)
            )

            queryset = queryset.filter(
                Q(department__isnull=True)
                |
                Q(
                    department_id=
                        department_id
                )
            )

            queryset = queryset.filter(
                Q(team__isnull=True)
                |
                Q(team_id=team_id)
            )

        category = (
            self.request.query_params
            .get("category")
        )

        active = (
            self.request.query_params
            .get("active")
        )

        if category:
            queryset = queryset.filter(
                category=category
            )

        if active == "true":
            queryset = queryset.filter(
                is_active=True
            )

        elif active == "false":
            queryset = queryset.filter(
                is_active=False
            )

        return queryset.distinct()

    def perform_create(
        self,
        serializer,
    ):

        serializer.save(
            company=
                self.request.user.company,
            created_by=
                self.request.user,
        )

    def perform_update(self, serializer):
        template = serializer.save()
        create_audit_log(user=self.request.user, company=template.company, request=self.request, action="UPDATE", description=f"Updated form template: {template.name}.", obj=template)

    def perform_destroy(
        self,
        instance,
    ):

        # Do not hard delete forms that may
        # have historical submissions.
        instance.is_active = False

        instance.save(
            update_fields=[
                "is_active"
            ]
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        template = self.get_object()
        if template.lifecycle_status == "ARCHIVED":
            raise ValidationError("Archived forms cannot be published.")
        template.lifecycle_status = "PUBLISHED"
        template.is_active = True
        template.save(update_fields=["lifecycle_status", "is_active"])
        create_audit_log(user=request.user, company=template.company, request=request, action="UPDATE", description=f"Published form template: {template.name}.", obj=template)
        return Response(self.get_serializer(template).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        template = self.get_object()
        template.lifecycle_status = "ARCHIVED"
        template.is_active = False
        template.save(update_fields=["lifecycle_status", "is_active"])
        create_audit_log(user=request.user, company=template.company, request=request, action="UPDATE", description=f"Archived form template: {template.name}.", obj=template)
        return Response(self.get_serializer(template).data)

    @action(detail=True, methods=["post"], url_path="reorder-fields")
    @transaction.atomic
    def reorder_fields(self, request, pk=None):
        template = self.get_object()
        field_ids = request.data.get("field_ids")
        if not isinstance(field_ids, list):
            raise ValidationError({"field_ids": "A list of field IDs is required."})
        fields = list(template.fields.filter(id__in=field_ids))
        if len(fields) != len(field_ids) or len(set(field_ids)) != len(field_ids):
            raise ValidationError({"field_ids": "Field IDs must be unique and belong to this form."})
        for order, field_id in enumerate(field_ids):
            template.fields.filter(id=field_id).update(order=order)
        template.version += 1
        template.save(update_fields=["version"])
        create_audit_log(user=request.user, company=template.company, request=request, action="UPDATE", description=f"Reordered fields for form template: {template.name}.", obj=template)
        return Response(self.get_serializer(template).data)


# ============================================================
# Form Submissions
# ============================================================

class FormSubmissionViewSet(
    viewsets.ModelViewSet
):

    serializer_class = (
        FormSubmissionSerializer
    )

    permission_classes = [
        IsAuthenticated,
        CanUseForms,
    ]

    def get_queryset(self):

        user = self.request.user

        queryset = (
            FormSubmission.objects
            .select_related(
                "company",
                "template",
                "submitted_by",
                "branch",
                "department",
                "team",
                "project",
                "task",
            )
        )

        return VisibilityService.form_submissions_queryset(
            user=user,
            queryset=queryset,
        )

    def perform_destroy(
        self,
        instance,
    ):

        if instance.status != "DRAFT":
            raise ValidationError(
                "Only draft submissions "
                "can be deleted."
            )

        if (
            instance.submitted_by_id
            != self.request.user.id
        ):
            raise ValidationError(
                "Only the author can delete "
                "this draft."
            )

        instance.delete()

    # --------------------------------------------------------
    # Submit
    # --------------------------------------------------------

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
    )
    def submit(
        self,
        request,
        pk=None,
    ):

        submission = (
            self.get_object()
        )

        workflow = None

        workflow_id = (
            request.data.get(
                "workflow"
            )
        )

        if workflow_id:

            try:
                workflow = (
                    WorkflowDefinition.objects.get(
                        id=workflow_id,
                        company=
                            submission.company,
                        target_type=
                            "FORM_SUBMISSION",
                        is_active=True,
                    )
                )

            except WorkflowDefinition.DoesNotExist:

                raise ValidationError({
                    "workflow":
                        "Invalid form submission workflow."
                })

        submission, instance = (
            FormSubmissionService.submit(
                submission=submission,
                user=request.user,
                workflow=workflow,
            )
        )

        return Response(
            {
                "message":
                    "Submission submitted successfully.",

                "submission":
                    self.get_serializer(
                        submission
                    ).data,

                "workflow_instance":
                    instance.id,
            },
            status=
                status.HTTP_200_OK,
        )