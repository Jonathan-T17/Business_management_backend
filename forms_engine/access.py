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
        from core.position_scope import PositionScope
        profile = getattr(user, 'employee_profile', None)
        eligible=Q(pk__in=[])
        if CS.has_company(user,C.SUBMIT_FORMS) or CS.has_company(user,C.USE_FORMS):
            base=Q()
            for field, actual in [('branch_id', user.branch_id), ('department_id', getattr(profile, 'department_id', None)), ('team_id', getattr(profile, 'team_id', None))]:
                base &= Q(**{field:actual}) | Q(**{field+'__isnull':True})
            eligible |= base
        for assignment in PositionScope.assignments(user).select_related("position").prefetch_related("branches"):
            if not assignment.position.capability_grants.filter(company_id=user.company_id,is_active=True,capability__in=[C.SUBMIT_FORMS,C.USE_FORMS]).exists(): continue
            branch_ids=[b.pk for b in assignment.branches.all() if b.is_active and b.company_id==user.company_id]
            condition=Q() if assignment.scope=="COMPANY" else Q(branch_id__in=branch_ids)
            if assignment.scope=="BRANCHES" and user.branch_id in branch_ids: condition |= Q(branch__isnull=True)
            for field in ("department_id","team_id"):
                condition &= Q(**{field:getattr(assignment.position,field)}) | Q(**{field+'__isnull':True})
            eligible |= condition
        queryset=queryset.filter(eligible)
        return queryset.filter(lifecycle_status='PUBLISHED', is_active=True).filter(Q(audience_roles=[]) | Q(audience_roles__contains=[user.role])).filter(Q(audience_user_ids=[]) | Q(audience_user_ids__contains=[str(user.pk)]))

    @classmethod
    def eligible(cls, user, template):
        return cls.templates(user, type(template).objects.filter(pk=template.pk)).exists()
