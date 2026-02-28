def generate_ai_summary(metrics: dict) -> str:
    if metrics["total"] == 0:
        return "No activity recorded for this period."

    completion_rate = round(
        (metrics["completed"] / metrics["total"]) * 100, 2
    )

    summary = (
        f"Out of {metrics['total']} tasks, "
        f"{metrics['completed']} were completed "
        f"({completion_rate}% completion rate). "
    )

    if metrics["overdue"] > 0:
        summary += (
            f"There are {metrics['overdue']} overdue tasks "
            "requiring attention."
        )
    else:
        summary += "No overdue tasks detected."

    return summary