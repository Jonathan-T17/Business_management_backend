from django.utils import timezone

def get_client_ip(request):
    from ipaddress import ip_address, ip_network
    from django.conf import settings
    try:
        peer = ip_address(request.META.get("REMOTE_ADDR", ""))
        networks = [ip_network(value) for value in getattr(settings, "TRUSTED_PROXY_NETWORKS", [])]
    except ValueError:
        return None
    if not any(peer in network for network in networks):
        return str(peer)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded or len(forwarded) > 2048:
        return str(peer)
    try:
        chain = [ip_address(value.strip()) for value in forwarded.split(",")]
    except ValueError:
        return str(peer)
    for address in reversed(chain):
        if not any(address in network for network in networks):
            return str(address)
    return str(peer)


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
