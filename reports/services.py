from django.db import transaction

from .models import Report, ReportField


@transaction.atomic
def create_report(*, validated_data, fields_data=None):
    """
    Centralized report creation service.
    """

    fields_data = fields_data or []

    report = Report.objects.create(
        **validated_data
    )

    ReportField.objects.bulk_create(
        [
            ReportField(
                report=report,
                **field,
            )
            for field in fields_data
        ]
    )

    return report


def collect_company_reports(company):
    """
    Lightweight reporting data for analytics/AI services.
    """

    reports = (
        Report.objects
        .filter(company=company)
        .select_related(
            "created_by",
            "branch",
            "project",
            "task",
        )
        .prefetch_related("fields")
    )

    return [
        {
            "id": str(report.id),
            "title": report.title,
            "description": report.description,
            "type": report.report_type,
            "visibility": report.visibility,
            "branch": (
                report.branch.name
                if report.branch
                else None
            ),
            "project": (
                report.project.name
                if report.project
                else None
            ),
            "task": (
                report.task.title
                if report.task
                else None
            ),
            "created_at": report.created_at,
        }
        for report in reports
    ]