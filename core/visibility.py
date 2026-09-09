from django.contrib.contenttypes.models import ContentType
from django.db.models import CharField, Q
from django.db.models.functions import Cast

from core.capabilities import Capabilities
from core.capability_service import CapabilityService


class VisibilityService:
    """Authoritative tenant object visibility.

    This service never grants tenant business-data visibility merely because an
    identity is a platform superuser. Platform endpoints use dedicated platform
    selectors and controlled support access will be implemented separately.
    """

    @staticmethod
    def _tenant_user(user):
        return CapabilityService.is_tenant_identity(user)

    @classmethod
    def same_company(cls, user, obj):
        if not cls._tenant_user(user):
            return False

        company_id = getattr(obj, "company_id", None)
        if company_id is None:
            activity = getattr(obj, "activity", None)
            company_id = getattr(activity, "company_id", None) if activity else None
        if company_id is None:
            company_id = getattr(getattr(obj, "company", None), "id", None)

        return company_id is not None and company_id == user.company_id

    @staticmethod
    def _workflow_instances_for(user, obj):
        from workflows.models import WorkflowInstance

        if not CapabilityService.is_tenant_identity(user):
            return WorkflowInstance.objects.none()

        content_type = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        return WorkflowInstance.objects.filter(
            company_id=user.company_id,
            content_type=content_type,
            object_id=str(obj.pk),
        )

    @classmethod
    def is_workflow_participant(cls, *, user, obj):
        from workflows.models import WorkflowStepRecipient

        if not cls._tenant_user(user):
            return False
        instances = cls._workflow_instances_for(user, obj)
        return instances.filter(submitted_by=user).exists() or WorkflowStepRecipient.objects.filter(
            step__workflow_instance__in=instances,
            user=user,
        ).exists()

    @staticmethod
    def delegated_user_ids(*, user, permission):
        from django.utils import timezone
        from organizations.models import EmployeeDelegation

        if not CapabilityService.is_tenant_identity(user):
            return []

        now = timezone.now()
        delegations = EmployeeDelegation.objects.filter(
            company_id=user.company_id,
            to_user=user,
            starts_at__lte=now,
            ends_at__gte=now,
            status__in=["SCHEDULED", "ACTIVE"],
        )
        return [
            delegation.from_user_id
            for delegation in delegations
            if permission in delegation.permissions
        ]

    @classmethod
    def has_delegated_access(cls, *, user, obj, permission):
        from workflows.models import WorkflowStepRecipient

        recipient_ids = cls.delegated_user_ids(user=user, permission=permission)
        if not recipient_ids:
            return False
        return WorkflowStepRecipient.objects.filter(
            step__workflow_instance__in=cls._workflow_instances_for(user, obj),
            user_id__in=recipient_ids,
        ).exists()

    @classmethod
    def workflow_object_ids(cls, *, user, model, delegated_permission=None):
        from workflows.models import WorkflowStepRecipient

        if not cls._tenant_user(user):
            return WorkflowStepRecipient.objects.none().values_list(
                "step__workflow_instance__object_id", flat=True
            )

        content_type = ContentType.objects.get_for_model(model, for_concrete_model=False)
        recipient_ids = [user.id]
        if delegated_permission:
            recipient_ids.extend(
                cls.delegated_user_ids(user=user, permission=delegated_permission)
            )

        return WorkflowStepRecipient.objects.filter(
            user_id__in=recipient_ids,
            step__workflow_instance__company_id=user.company_id,
            step__workflow_instance__content_type=content_type,
        ).values_list("step__workflow_instance__object_id", flat=True).distinct()

    # ------------------------------------------------------------------
    # Projects / tasks
    # ------------------------------------------------------------------
    @classmethod
    def projects_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        if CapabilityService.has(user, Capabilities.MANAGE_PROJECTS):
            # Project administration may see project metadata/configuration.
            return queryset.distinct()

        return queryset.filter(
            Q(memberships__user=user) | Q(created_by=user)
        ).distinct()

    @classmethod
    def can_view_project_content(cls, *, user, project):
        if not cls.same_company(user, project):
            return False
        return project.created_by_id == user.id or project.memberships.filter(user=user).exists()

    @classmethod
    def tasks_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        # Task content visibility follows project participation, not company role.
        return queryset.filter(
            Q(project__memberships__user=user)
            | Q(project__created_by=user)
            | Q(assignees=user)
            | Q(created_by=user)
        ).distinct()

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------
    @classmethod
    def can_view_report(cls, user, report):
        if not cls.same_company(user, report):
            return False
        if report.created_by_id == user.id:
            return True
        if CapabilityService.has(user, Capabilities.VIEW_ALL_REPORTS):
            return True
        if cls.is_workflow_participant(user=user, obj=report):
            return True
        if cls.has_delegated_access(user=user, obj=report, permission="RECEIVE_REPORTS"):
            return True
        if cls.has_delegated_access(user=user, obj=report, permission="APPROVE_REPORTS"):
            return True
        if report.visibility == "COMPANY":
            return True
        if report.visibility == "BRANCH":
            return bool(user.branch_id and report.branch_id == user.branch_id)
        if report.visibility == "PROJECT":
            return bool(report.project_id and cls.can_view_project_content(user=user, project=report.project))
        return False

    @classmethod
    def reports_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        if CapabilityService.has(user, Capabilities.VIEW_ALL_REPORTS):
            return queryset

        from reports.models import Report

        workflow_ids = cls.workflow_object_ids(
            user=user, model=Report, delegated_permission="RECEIVE_REPORTS"
        ).union(
            cls.workflow_object_ids(
                user=user, model=Report, delegated_permission="APPROVE_REPORTS"
            )
        )
        workflow_ids = [str(item) for item in workflow_ids]

        return queryset.filter(
            Q(created_by=user)
            | Q(visibility="COMPANY")
            | Q(visibility="BRANCH", branch_id=user.branch_id)
            | Q(visibility="PROJECT", project__memberships__user=user)
            | Q(visibility="PROJECT", project__created_by=user)
            | Q(id__in=workflow_ids)
        ).distinct()

    # ------------------------------------------------------------------
    # Forms / requests
    # ------------------------------------------------------------------
    @classmethod
    def form_submissions_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        from forms_engine.models import FormSubmission

        workflow_ids = cls.workflow_object_ids(
            user=user,
            model=FormSubmission,
            delegated_permission="REVIEW_SUBMISSIONS",
        )
        return queryset.filter(
            Q(submitted_by=user) | Q(id__in=[str(item) for item in workflow_ids])
        ).distinct()

    @classmethod
    def business_requests_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id).annotate(
            workflow_object_id=Cast("id", output_field=CharField())
        )
        from requests_app.models import BusinessRequest

        workflow_ids = cls.workflow_object_ids(
            user=user,
            model=BusinessRequest,
            delegated_permission="APPROVE_REQUESTS",
        )
        return queryset.filter(
            Q(requester=user) | Q(workflow_object_id__in=workflow_ids)
        ).distinct()

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    @classmethod
    def documents_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id, is_active=True)
        profile = getattr(user, "employee_profile", None)
        conditions = Q(visibility="COMPANY") | Q(visibility="PRIVATE", owner=user)

        if user.branch_id:
            conditions |= Q(visibility="BRANCH", branch_id=user.branch_id)
        if profile and profile.department_id:
            conditions |= Q(visibility="DEPARTMENT", department_id=profile.department_id)
        if profile and profile.team_id:
            conditions |= Q(visibility="TEAM", team_id=profile.team_id)
        if CapabilityService.has(user, Capabilities.VIEW_MANAGEMENT_DOCUMENTS):
            conditions |= Q(visibility="MANAGEMENT")

        # Sensitive document categories remain owner-only until a dedicated
        # sensitive-document capability/policy is introduced.
        return queryset.filter(conditions).filter(
            Q(category__sensitive=False) | Q(category__isnull=True) | Q(owner=user)
        ).distinct()

    # ------------------------------------------------------------------
    # Field operations
    # ------------------------------------------------------------------
    @classmethod
    def field_objects_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        if CapabilityService.has(user, Capabilities.MANAGE_FIELD_OPERATIONS):
            return queryset
        return queryset.filter(employee=user)

    @classmethod
    def field_activities_queryset(cls, *, user, queryset):
        return cls.field_objects_queryset(user=user, queryset=queryset)

    @classmethod
    def can_view_field_object(cls, *, user, obj):
        from field_operations.models import FieldActivity, FieldStop

        if isinstance(obj, FieldActivity):
            return cls.field_activities_queryset(
                user=user, queryset=FieldActivity.objects.filter(pk=obj.pk)
            ).exists()
        if isinstance(obj, FieldStop):
            return cls.can_view_field_object(user=user, obj=obj.activity)
        return False

    # ------------------------------------------------------------------
    # Attachments / generic source visibility
    # ------------------------------------------------------------------
    @classmethod
    def can_view_attachment(cls, *, user, attachment):
        if not cls._tenant_user(user) or attachment.company_id != user.company_id:
            return False

        target = attachment.content_object
        if target is None:
            return False

        key = (attachment.content_type.app_label, attachment.content_type.model)
        if key == ("reports", "report"):
            return cls.can_view_report(user=user, report=target)
        if key == ("forms_engine", "formsubmission"):
            return cls.form_submissions_queryset(
                user=user, queryset=target.__class__.objects.filter(pk=target.pk)
            ).exists()
        if key == ("requests_app", "businessrequest"):
            return cls.business_requests_queryset(
                user=user, queryset=target.__class__.objects.filter(pk=target.pk)
            ).exists()
        if key[0] == "field_operations":
            return cls.can_view_field_object(user=user, obj=target)
        if key[0] == "projects":
            return cls.can_view_project_content(user=user, project=target)
        if key[0] == "tasks":
            return cls.tasks_queryset(
                user=user, queryset=target.__class__.objects.filter(pk=target.pk)
            ).exists()
        return False

    @classmethod
    def can_view_generic_object(cls, *, user, obj):
        from field_operations.models import FieldActivity, FieldStop
        from forms_engine.models import FormSubmission
        from projects.models import Project
        from reports.models import Report
        from requests_app.models import BusinessRequest
        from tasks.models import Task

        if isinstance(obj, Report):
            return cls.can_view_report(user, obj)
        if isinstance(obj, FormSubmission):
            return cls.form_submissions_queryset(
                user=user, queryset=FormSubmission.objects.filter(pk=obj.pk)
            ).exists()
        if isinstance(obj, BusinessRequest):
            return cls.business_requests_queryset(
                user=user, queryset=BusinessRequest.objects.filter(pk=obj.pk)
            ).exists()
        if isinstance(obj, (FieldActivity, FieldStop)):
            return cls.can_view_field_object(user=user, obj=obj)
        if isinstance(obj, Project):
            return cls.can_view_project_content(user=user, project=obj)
        if isinstance(obj, Task):
            return cls.tasks_queryset(
                user=user, queryset=Task.objects.filter(pk=obj.pk)
            ).exists()
        return False

    # ------------------------------------------------------------------
    # Official records
    # ------------------------------------------------------------------
    @classmethod
    def official_records_queryset(cls, *, user, queryset):
        if not cls._tenant_user(user):
            return queryset.none()

        queryset = queryset.filter(company_id=user.company_id)
        # Official-record visibility must preserve source visibility. The
        # VIEW_OFFICIAL_RECORDS capability permits using the records module; it
        # does not override the source object's confidentiality.
        allowed = []
        for record in queryset:
            source = record.source_object
            if source and cls.can_view_generic_object(user=user, obj=source):
                allowed.append(record.pk)
        return queryset.filter(pk__in=allowed)

    @staticmethod
    def reports(user):
        from reports.models import Report

        return VisibilityService.reports_queryset(user=user, queryset=Report.objects.all())
