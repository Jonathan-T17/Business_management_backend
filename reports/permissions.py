def can_view_report(user, report):
    if user.role == 'SUPERUSER':
        return True

    if report.visibility == 'PRIVATE':
        return report.created_by == user

    if report.visibility == 'COMPANY':
        return user.company == report.company

    if report.visibility == 'BRANCH':
        return user.branch == report.branch

    if report.visibility == 'PROJECT':
        return report.project and report.project.company == user.company

    return False