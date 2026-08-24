from django.utils import timezone

def get_client_ip(request):
    """
    Extract client IP address from request headers.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def user_company(user):
    return getattr(user, "company", None)


def user_branch(user):
    return getattr(user, "branch", None)


def is_same_company(user, obj):
    return hasattr(obj, "company") and obj.company == user.company


def is_same_branch(user, obj):
    return hasattr(obj, "branch") and obj.branch == user.branch


def get_company(obj):
    if hasattr(obj, "company"):
        return obj.company
    if hasattr(obj, "project"):
        return obj.project.company
    if hasattr(obj, "report"):
        return obj.report.company
    return None


def get_branch(obj):
    if hasattr(obj, "branch"):
        return obj.branch
    if hasattr(obj, "project"):
        return obj.project.branch
    return None
