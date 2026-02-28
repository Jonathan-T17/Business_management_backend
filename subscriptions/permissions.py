from rest_framework.permissions import BasePermission


class HasActiveSubscription(BasePermission):
    def has_permission(self, request, view):
        company = getattr(request.user, "company", None)
        if not company:
            return False

        return hasattr(company, "subscription") and company.subscription.is_active