from django.utils import timezone
from tasks.models import Task
from reports.models import Report
from projects.models import Project


def collect_company_data(company):

    tasks = Task.objects.filter(company=company)
    reports = Report.objects.filter(company=company)
    projects = Project.objects.filter(company=company)

    data = {
        "total_tasks": tasks.count(),
        "completed_tasks": tasks.filter(status="completed").count(),
        "pending_tasks": tasks.filter(status="pending").count(),
        "overdue_tasks": tasks.filter(status="pending", due_date__lt=timezone.now()).count(),
        "total_reports": reports.count(),
        "active_projects": projects.filter(is_active=True).count(),
    }

    return data