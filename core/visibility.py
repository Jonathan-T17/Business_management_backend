from reports.models import Report


class VisibilityService:

    @staticmethod
    def can_view_report(user, report):

        if user.role == "SUPERUSER":
            return True

        if report.visibility == "PRIVATE":
            return report.created_by == user

        if report.visibility == "COMPANY":
            return report.company == user.company

        if report.visibility == "BRANCH":
            return report.branch == user.branch

        if report.visibility == "PROJECT":
            return (
                report.project is not None
                and report.project.company == user.company
            )

        return False

    @staticmethod
    def reports(user):

        reports = Report.objects.all()

        visible = []

        for report in reports:
            if VisibilityService.can_view_report(
                user,
                report,
            ):
                visible.append(report.id)

        return Report.objects.filter(
            id__in=visible
        )