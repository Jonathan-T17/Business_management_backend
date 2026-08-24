from users.models import User

from .models import AIInsight, AIAnalyticsRecord
from .services import (
    generate_company_metrics,
    generate_project_metrics,
    generate_branch_metrics,
)


def generate_company_summary(company):
    data = generate_company_metrics(company)

    summary = (
        f"The company currently manages "
        f"{data['total_tasks']} active tasks across "
        f"{data['active_projects']} active projects. "
        f"{data['completed_tasks']} tasks are completed, "
        f"giving a completion rate of "
        f"{data['completion_rate']:.1f}%. "
        f"There are {data['pending_tasks']} pending, "
        f"{data['in_progress_tasks']} in-progress, "
        f"{data['blocked_tasks']} blocked and "
        f"{data['overdue_tasks']} overdue tasks."
    )

    insight = AIInsight.objects.create(
        company=company,
        insight_type="COMPANY_SUMMARY",
        severity="INFO",
        title="Company Performance Summary",
        summary=summary,
        metrics=data,
    )

    AIAnalyticsRecord.objects.create(
        company=company,
        level="COMPANY",
        summary=summary,
        metrics=data,
    )

    return insight


def generate_project_summary(project):
    data = generate_project_metrics(project)

    summary = (
        f"Project '{project.name}' currently has "
        f"{data['total_tasks']} active tasks. "
        f"{data['completed_tasks']} are completed, "
        f"with a completion rate of "
        f"{data['completion_rate']:.1f}%. "
        f"There are {data['overdue_tasks']} overdue tasks."
    )

    severity = "INFO"

    if data["overdue_rate"] >= 30:
        severity = "HIGH"
    elif data["overdue_rate"] >= 15:
        severity = "MEDIUM"

    insight = AIInsight.objects.create(
        company=project.company,
        project=project,
        insight_type="PROJECT_SUMMARY",
        severity=severity,
        title=f"Project Performance: {project.name}",
        summary=summary,
        metrics=data,
    )

    AIAnalyticsRecord.objects.create(
        company=project.company,
        project=project,
        level="PROJECT",
        summary=summary,
        metrics=data,
    )

    return insight


def generate_branch_summary(branch):
    data = generate_branch_metrics(branch)

    summary = (
        f"Branch '{branch.name}' currently manages "
        f"{data['total_tasks']} active tasks across "
        f"{data['active_projects']} active projects. "
        f"The completion rate is "
        f"{data['completion_rate']:.1f}%, with "
        f"{data['overdue_tasks']} overdue tasks."
    )

    insight = AIInsight.objects.create(
        company=branch.company,
        branch=branch,
        insight_type="BRANCH_SUMMARY",
        severity="INFO",
        title=f"Branch Performance: {branch.name}",
        summary=summary,
        metrics=data,
    )

    AIAnalyticsRecord.objects.create(
        company=branch.company,
        branch=branch,
        level="BRANCH",
        summary=summary,
        metrics=data,
    )

    return insight


def detect_workload_imbalance(company):
    alerts = []

    users = User.objects.filter(
        company=company,
        is_active=True,
    )

    for user in users:
        task_count = user.tasks.filter(
            company=company,
            is_active=True,
        ).count()

        if task_count > 10:
            name = (
                user.get_full_name()
                or getattr(user, "full_name", None)
                or user.email
            )

            insight = AIInsight.objects.create(
                company=company,
                user=user,
                insight_type="WORKLOAD_ALERT",
                severity="MEDIUM",
                title="Workload Imbalance Detected",
                summary=(
                    f"{name} currently has "
                    f"{task_count} active assigned tasks."
                ),
                metrics={
                    "task_count": task_count,
                },
            )

            alerts.append(insight)

    return alerts


def detect_company_risks(company):
    data = generate_company_metrics(company)

    alerts = []

    if data["overdue_rate"] >= 30:
        alerts.append(
            AIInsight.objects.create(
                company=company,
                insight_type="RISK_ALERT",
                severity="HIGH",
                title="High Overdue Task Risk",
                summary=(
                    f"{data['overdue_rate']:.1f}% of active tasks "
                    f"are overdue."
                ),
                metrics=data,
            )
        )

    if data["blocked_tasks"] > 0:
        alerts.append(
            AIInsight.objects.create(
                company=company,
                insight_type="RISK_ALERT",
                severity="MEDIUM",
                title="Blocked Tasks Detected",
                summary=(
                    f"{data['blocked_tasks']} active tasks "
                    f"are currently blocked."
                ),
                metrics=data,
            )
        )

    return alerts


def generate_company_insights(company):
    results = [
        generate_company_summary(company),
    ]

    results.extend(
        detect_workload_imbalance(company)
    )

    results.extend(
        detect_company_risks(company)
    )

    return results