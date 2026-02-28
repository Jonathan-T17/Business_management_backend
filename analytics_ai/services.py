from activity.models import ActivityLog
from reports.models import Report
from comments.models import Comment


def collect_company_text_data(company):
    return {
        "reports": list(
            Report.objects.filter(company=company)
            .values_list("content", flat=True)
        ),
        "comments": list(
            Comment.objects.filter(company=company)
            .values_list("content", flat=True)
        ),
        "activity": list(
            ActivityLog.objects.filter(company=company)
            .values_list("action", flat=True)
        ),
    }