from django.db.models import Q
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService as CS


class FormAccess:
    @staticmethod
    def has(user, capability):
        return CS.is_tenant_identity(user) and CS.has(user, capability)

    @classmethod
    def can_submit(cls, user):
        return cls.has(user, C.SUBMIT_FORMS) or cls.has(user, C.USE_FORMS)

    @classmethod
    def templates(cls, user, queryset, *, builder=False):
        if not CS.is_tenant_identity(user):
            return queryset.none()
        queryset = queryset.filter(company_id=user.company_id)
        if builder and (cls.has(user, C.MANAGE_FORM_TEMPLATES) or cls.has(user, C.PUBLISH_FORM_TEMPLATES)):
            return queryset
        if not cls.can_submit(user):
            return queryset.none()
        profile = getattr(user, 'employee_profile', None)
        for field, actual in [('branch_id', user.branch_id), ('department_id', getattr(profile, 'department_id', None)), ('team_id', getattr(profile, 'team_id', None))]:
            queryset = queryset.filter(Q(**{field: actual}) | Q(**{field+'__isnull': True}))
        return queryset.filter(lifecycle_status='PUBLISHED', is_active=True).filter(Q(audience_roles=[]) | Q(audience_roles__contains=[user.role])).filter(Q(audience_user_ids=[]) | Q(audience_user_ids__contains=[str(user.pk)]))

    @classmethod
    def eligible(cls, user, template):
        return cls.templates(user, type(template).objects.filter(pk=template.pk)).exists()
