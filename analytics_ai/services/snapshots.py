from analytics_ai.models import AnalyticsSnapshot
from .metrics import calculate_task_metrics
from .ai import generate_ai_summary
from tasks.models import Task


def generate_company_snapshot(company):

    tasks = Task.objects.filter(company=company)

    metrics = calculate_task_metrics(tasks)
    ai_summary = generate_ai_summary(metrics)

    snapshot = AnalyticsSnapshot.objects.create(
        company=company,
        snapshot_type="company",
        total_tasks=metrics["total"],
        completed_tasks=metrics["completed"],
        overdue_tasks=metrics["overdue"],
        ai_summary=ai_summary,
    )

    return snapshot