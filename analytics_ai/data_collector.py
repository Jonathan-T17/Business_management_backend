from django.utils import timezone

from tasks.models import Task
from reports.models import Report
from projects.models import Project
from comments.models import Comment


def collect_company_data(company):
    today = timezone.localdate()

    tasks = Task.objects.filter(
        company=company,
        is_active=True,
    )

    projects = Project.objects.filter(
        company=company,
        is_active=True,
    )

    reports = Report.objects.filter(
        company=company,
    )

    comments = Comment.objects.filter(
        company=company,
    )

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="done").count()
    pending_tasks = tasks.filter(status="pending").count()
    in_progress_tasks = tasks.filter(status="in_progress").count()
    blocked_tasks = tasks.filter(status="blocked").count()

    overdue_tasks = tasks.filter(
        due_date__lt=today,
    ).exclude(
        status="done",
    ).count()

    completion_rate = (
        (completed_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    overdue_rate = (
        (overdue_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "blocked_tasks": blocked_tasks,
        "overdue_tasks": overdue_tasks,
        "total_projects": Project.objects.filter(
            company=company
        ).count(),
        "active_projects": projects.count(),
        "total_reports": reports.count(),
        "total_comments": comments.count(),
        "completion_rate": round(completion_rate, 2),
        "overdue_rate": round(overdue_rate, 2),
    }


def collect_project_data(project):
    today = timezone.localdate()

    tasks = Task.objects.filter(
        project=project,
        company=project.company,
        is_active=True,
    )

    reports = Report.objects.filter(
        project=project,
        company=project.company,
    )

    comments = Comment.objects.filter(
        project=project,
        company=project.company,
    )

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="done").count()
    pending_tasks = tasks.filter(status="pending").count()
    in_progress_tasks = tasks.filter(status="in_progress").count()
    blocked_tasks = tasks.filter(status="blocked").count()

    overdue_tasks = tasks.filter(
        due_date__lt=today,
    ).exclude(
        status="done",
    ).count()

    completion_rate = (
        (completed_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    overdue_rate = (
        (overdue_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "blocked_tasks": blocked_tasks,
        "overdue_tasks": overdue_tasks,
        "total_reports": reports.count(),
        "total_comments": comments.count(),
        "completion_rate": round(completion_rate, 2),
        "overdue_rate": round(overdue_rate, 2),
    }


def collect_branch_data(branch):
    today = timezone.localdate()

    tasks = Task.objects.filter(
        company=branch.company,
        project__branches=branch,
        is_active=True,
    ).distinct()

    projects = Project.objects.filter(
        company=branch.company,
        branches=branch,
        is_active=True,
    ).distinct()

    reports = Report.objects.filter(
        company=branch.company,
        branch=branch,
    )

    comments = Comment.objects.filter(
        company=branch.company,
        project__branches=branch,
    ).distinct()

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status="done").count()
    pending_tasks = tasks.filter(status="pending").count()
    in_progress_tasks = tasks.filter(status="in_progress").count()
    blocked_tasks = tasks.filter(status="blocked").count()

    overdue_tasks = tasks.filter(
        due_date__lt=today,
    ).exclude(
        status="done",
    ).count()

    completion_rate = (
        (completed_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    overdue_rate = (
        (overdue_tasks / total_tasks) * 100
        if total_tasks
        else 0
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "blocked_tasks": blocked_tasks,
        "overdue_tasks": overdue_tasks,
        "total_projects": projects.count(),
        "active_projects": projects.count(),
        "total_reports": reports.count(),
        "total_comments": comments.count(),
        "completion_rate": round(completion_rate, 2),
        "overdue_rate": round(overdue_rate, 2),
    }