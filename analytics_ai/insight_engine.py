from .models import AIInsight
from .data_collector import collect_company_data

from django.db.models import Count
from users.models import User



def generate_company_summary(company):

    data = collect_company_data(company)

    completion_rate = 0

    if data["total_tasks"] > 0:
        completion_rate = (
            data["completed_tasks"] / data["total_tasks"]
        ) * 100

    summary = (
        f"The company currently manages {data['total_tasks']} tasks "
        f"across {data['active_projects']} active projects. "
        f"{data['completed_tasks']} tasks have been completed "
        f"with a completion rate of {completion_rate:.1f}%. "
        f"There are {data['pending_tasks']} pending tasks "
        f"and {data['overdue_tasks']} overdue tasks."
    )

    insight = AIInsight.objects.create(
        company=company,
        insight_type="COMPANY_SUMMARY",
        title="Company Performance Summary",
        summary=summary
    )

    return insight








def detect_workload_imbalance(company):

    users = User.objects.filter(company=company)

    alerts = []

    for user in users:
        task_count = user.assigned_tasks.count()

        if task_count > 10:

            insight = AIInsight.objects.create(
                company=company,
                insight_type="WORKLOAD_ALERT",
                title="Workload Imbalance Detected",
                summary=f"{user.full_name} currently has {task_count} assigned tasks."
            )

            alerts.append(insight)

    return alerts