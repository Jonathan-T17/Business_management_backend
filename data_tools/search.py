from dataclasses import dataclass
from typing import Optional

from django.db.models import Q

from core.roles import Roles
from core.tenant import TenantService
from core.visibility import VisibilityService
from documents.models import Document
from field_operations.models import FieldActivity
from forms_engine.models import FormSubmission
from organizations.models import EmployeeProfile
from planning.models import CompanyPlan
from projects.models import Project
from records_management.models import OfficialRecord
from reports.models import Report
from requests_app.models import BusinessRequest
from tasks.models import Task


@dataclass
class SearchResult:
    type: str
    id: str
    title: str
    subtitle: str = ""
    url: str = ""
    status: Optional[str] = None


class GlobalSearchService:
    DEFAULT_LIMIT = 10

    @classmethod
    def search(cls, *, user, query, limit=None):
        query = query.strip()
        if len(query) < 2:
            return []

        try:
            limit = min(int(limit or cls.DEFAULT_LIMIT), 50)
        except (TypeError, ValueError):
            limit = cls.DEFAULT_LIMIT

        results = []
        for finder in (
            cls._employees,
            cls._projects,
            cls._tasks,
            cls._reports,
            cls._requests,
            cls._forms,
            cls._plans,
            cls._documents,
            cls._official_records,
            cls._field_activities,
        ):
            results.extend(finder(user=user, query=query, limit=limit))
        return results[:100]

    @staticmethod
    def _employees(*, user, query, limit):
        if not user.company_id:
            return []
        items = EmployeeProfile.objects.filter(
            company=user.company,
        ).select_related("user", "position").filter(
            Q(user__email__icontains=query)
            | Q(user__full_name__icontains=query)
            | Q(employee_id__icontains=query)
            | Q(position__title__icontains=query)
        )[:limit]
        return [SearchResult(
            type="employee", id=str(item.pk), title=item.user.full_name,
            subtitle=item.position.title if item.position else item.user.email,
            url=f"/employees/{item.pk}", status=item.status,
        ) for item in items]

    @staticmethod
    def _projects(*, user, query, limit):
        queryset = Project.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).filter(company=user.company)
        if user.role not in (Roles.SUPERUSER, Roles.ADMIN):
            queryset = queryset.filter(memberships__user=user)
        return [SearchResult(
            type="project", id=str(item.pk), title=item.name,
            subtitle="Project", url=f"/projects/{item.pk}",
            status="active" if item.is_active else "inactive",
        ) for item in queryset[:limit]]

    @staticmethod
    def _tasks(*, user, query, limit):
        queryset = TenantService.tasks(user).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
        return [SearchResult(
            type="task", id=str(item.pk), title=item.title,
            subtitle=item.project.name, url=f"/tasks/{item.pk}", status=item.status,
        ) for item in queryset.select_related("project")[:limit]]

    @staticmethod
    def _reports(*, user, query, limit):
        queryset = VisibilityService.reports_queryset(
            user=user,
            queryset=Report.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="report", id=str(item.pk), title=item.title,
            subtitle="Report", url=f"/reports/{item.pk}", status=item.status,
        ) for item in queryset]

    @staticmethod
    def _requests(*, user, query, limit):
        queryset = VisibilityService.business_requests_queryset(
            user=user,
            queryset=BusinessRequest.objects.filter(
                Q(request_number__icontains=query)
                | Q(title__icontains=query)
                | Q(description__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="request", id=str(item.pk), title=item.title,
            subtitle=item.request_number, url=f"/requests/{item.pk}", status=item.status,
        ) for item in queryset]

    @staticmethod
    def _forms(*, user, query, limit):
        queryset = VisibilityService.form_submissions_queryset(
            user=user,
            queryset=FormSubmission.objects.filter(
                Q(template__name__icontains=query) | Q(id__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="form_submission", id=str(item.pk), title=str(item.template),
            subtitle="Form submission", url=f"/form-submissions/{item.pk}", status=item.status,
        ) for item in queryset]

    @staticmethod
    def _plans(*, user, query, limit):
        queryset = CompanyPlan.objects.filter(
            company=user.company,
        ).filter(Q(title__icontains=query) | Q(description__icontains=query))
        if user.role not in (Roles.SUPERUSER, Roles.ADMIN):
            queryset = queryset.filter(
                Q(visibility="COMPANY")
                | Q(visibility="BRANCH", branch_id=user.branch_id)
                | Q(visibility="PRIVATE", owner=user)
            )
        return [SearchResult(
            type="plan", id=str(item.pk), title=item.title,
            subtitle="Plan", url=f"/plans/{item.pk}", status=item.status,
        ) for item in queryset[:limit]]

    @staticmethod
    def _documents(*, user, query, limit):
        queryset = VisibilityService.documents_queryset(
            user=user,
            queryset=Document.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="document", id=str(item.pk), title=item.title,
            subtitle=item.document_number, url=f"/documents/{item.pk}", status=item.status,
        ) for item in queryset]

    @staticmethod
    def _official_records(*, user, query, limit):
        queryset = VisibilityService.official_records_queryset(
            user=user,
            queryset=OfficialRecord.objects.filter(
                Q(record_number__icontains=query) | Q(title__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="official_record", id=str(item.pk), title=item.title,
            subtitle=item.record_number, url=f"/official-records/{item.pk}", status=item.status,
        ) for item in queryset]

    @staticmethod
    def _field_activities(*, user, query, limit):
        queryset = VisibilityService.field_activities_queryset(
            user=user,
            queryset=FieldActivity.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ),
        )[:limit]
        return [SearchResult(
            type="field_activity", id=str(item.pk), title=item.title,
            subtitle=item.activity_type, url=f"/field-activities/{item.pk}", status=item.status,
        ) for item in queryset]