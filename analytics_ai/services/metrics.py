from django.utils.timezone import now
from tasks.models import Task


def calculate_task_metrics(queryset):
    total = queryset.count()
    completed = queryset.filter(status="completed").count()
    overdue = queryset.filter(
        due_date__lt=now(),
        status__in=["pending", "in_progress"]
    ).count()

    return {
        "total": total,
        "completed": completed,
        "overdue": overdue,
    }


def plan_progress(plan):
    total = plan.items.count()

    completed = plan.items.filter(
        status="COMPLETED"
    ).count()

    percentage = (
        completed / total * 100
        if total
        else 0
    )

    return {
        "total": total,
        "completed": completed,
        "percentage": round(
            percentage,
            2,
        ),
    }