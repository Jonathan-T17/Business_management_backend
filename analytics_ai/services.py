from django.db.models import Count

from tasks.models import Task

from .data_collector import (
    collect_company_data,
    collect_project_data,
    collect_branch_data,
)


def calculate_collaboration_score(project):
    """
    Simple deterministic collaboration score.

    Score is based on:
    - number of project members
    - number of tasks with multiple assignees
    - number of comments
    """

    members = project.memberships.count()

    collaborative_tasks = Task.objects.filter(
        project=project,
        is_active=True,
    ).annotate(
        assignee_count=Count("assignees", distinct=True)
    ).filter(
        assignee_count__gt=1
    ).count()

    comments = project.comments.count()

    score = (
        min(members * 5, 30)
        + min(collaborative_tasks * 5, 35)
        + min(comments, 35)
    )

    return round(min(score, 100), 2)


def calculate_workload_balance_score(company):
    """
    Measures how evenly active tasks are distributed.

    100 = very balanced
    0 = highly concentrated workload.
    """

    users = company.users.all()

    workloads = []

    for user in users:
        count = user.tasks.filter(
            company=company,
            is_active=True,
        ).count()

        workloads.append(count)

    if not workloads:
        return 100.0

    average = sum(workloads) / len(workloads)

    if average == 0:
        return 100.0

    maximum = max(workloads)

    imbalance_ratio = min(
        maximum / average,
        3
    )

    score = 100 - (
        ((imbalance_ratio - 1) / 2) * 100
    )

    return round(max(score, 0), 2)


def generate_company_metrics(company):
    data = collect_company_data(company)

    data["workload_balance_score"] = (
        calculate_workload_balance_score(company)
    )

    return data


def generate_project_metrics(project):
    data = collect_project_data(project)

    data["collaboration_score"] = (
        calculate_collaboration_score(project)
    )

    return data


def generate_branch_metrics(branch):
    return collect_branch_data(branch)