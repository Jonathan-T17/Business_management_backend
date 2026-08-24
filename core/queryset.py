from core.roles import Roles


class TenantQuerysetMixin:

    def for_user(self, user):

        if user.role == Roles.SUPERUSER:
            return self

        return self.filter(company=user.company)



 


class TenantQuerySetMixin:

    def filter_company(self, queryset):

        user = self.request.user

        if user.role == Roles.SUPERUSER:
            return queryset

        return queryset.filter(company=user.company)

    def filter_branch(self, queryset):

        user = self.request.user

        if user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        ):
            return queryset

        if user.role == Roles.MANAGER:
            return queryset.filter(branch=user.branch)

        return queryset.filter(created_by=user)