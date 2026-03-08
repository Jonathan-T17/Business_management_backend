from .models import Report


def collect_company_reports(company):

    reports = Report.objects.filter(company=company)

    return [
        {
            "title": r.title,
            "description": r.description,
            "type": r.report_type,
            "created_at": r.created_at,
        }
        for r in reports
    ]