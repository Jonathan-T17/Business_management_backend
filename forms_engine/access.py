from django.db.models import Q
from core.capabilities import Capabilities as C
from core.capability_service import CapabilityService as CS


class FormAccess:
    @classmethod
    def filing_branches(cls, user, template):
        """Choices narrow existing submission authority; they never grant it."""
        from companies.models import Branch
        from core.position_scope import PositionScope
        branches = Branch.objects.filter(company_id=user.company_id, is_active=True)
        if not cls.eligible(user, template):
            return branches.none()
        if CS.has_company(user, C.SUBMIT_FORMS) or CS.has_company(user, C.USE_FORMS):
            allowed = branches
        else:
            ids = PositionScope.branches_for(user, C.SUBMIT_FORMS) | PositionScope.branches_for(user, C.USE_FORMS)
            if cls.default_member_access(user):
                ids.add(getattr(cls.starting_branch(user), 'pk', None))
            allowed = branches.filter(pk__in=ids)
        if template.branch_id:
            return allowed.filter(pk=template.branch_id)
        # Department/team and targeted audience forms retain their existing context.
        if template.department_id or template.team_id or template.audience_branch_ids or template.audience_position_ids:
            return allowed.filter(pk=getattr(cls.starting_branch(user, template), 'pk', None))
        return allowed.order_by('name', 'id')

    @staticmethod
    def starting_branch(user, template=None):
        from core.position_scope import PositionScope
        if template and template.branch_id:
            return template.branch
        primary = PositionScope.primary_position(user)
        if primary and primary.primary_scope == 'BRANCH' and PositionScope.primary_capabilities(user) & {C.USE_FORMS, C.SUBMIT_FORMS}:
            return primary.branch
        return user.branch

    @staticmethod
    def has(user, capability):
        return CS.is_tenant_identity(user) and CS.has(user, capability)

    @staticmethod
    def default_member_access(user):
        from companies.invitation_access import awaiting_position
        return bool(CS.is_tenant_identity(user) and user.is_active and user.company.is_active and not getattr(user, 'is_deleted', False)
                    and user.role in {'ADMIN','MANAGER','EMPLOYEE'} and not awaiting_position(user))

    @classmethod
    def can_submit(cls, user):
        return cls.has(user, C.SUBMIT_FORMS) or cls.has(user, C.USE_FORMS)

    @classmethod
    def templates(cls, user, queryset, *, builder=False, history=False):
        if not CS.is_tenant_identity(user):
            return queryset.none()
        queryset = queryset.filter(company_id=user.company_id)
        if not history:
            queryset = queryset.filter(workspace_deleted=False)
        if builder and (cls.has(user, C.MANAGE_FORM_TEMPLATES) or cls.has(user, C.PUBLISH_FORM_TEMPLATES)):
            return queryset.exclude(lifecycle_status='ARCHIVED')
        if not cls.can_submit(user):
            return queryset.none()
        from core.position_scope import PositionScope
        profile = getattr(user, 'employee_profile', None)
        eligible=Q(pk__in=[])
        if cls.default_member_access(user) or CS.has_company(user,C.SUBMIT_FORMS) or CS.has_company(user,C.USE_FORMS):
            base=Q()
            for field, actual in [('branch_id', getattr(cls.starting_branch(user), 'pk', None)), ('department_id', getattr(profile, 'department_id', None)), ('team_id', getattr(profile, 'team_id', None))]:
                base &= Q(**{field:actual}) | Q(**{field+'__isnull':True})
            eligible |= base
        primary = PositionScope.primary_position(user)
        if primary and primary.primary_scope == "BRANCH" and PositionScope.primary_capabilities(user) & {C.SUBMIT_FORMS, C.USE_FORMS}:
            condition = Q(branch_id=primary.branch_id) | Q(branch__isnull=True)
            for field in ("department_id", "team_id"):
                condition &= Q(**{field: getattr(primary, field)}) | Q(**{field + "__isnull": True})
            eligible |= condition
        for assignment in PositionScope.assignments(user).select_related("position").prefetch_related("branches"):
            if not assignment.position.capability_grants.filter(company_id=user.company_id,is_active=True,capability__in=[C.SUBMIT_FORMS,C.USE_FORMS]).exists(): continue
            branch_ids=[b.pk for b in assignment.branches.all() if b.is_active and b.company_id==user.company_id]
            condition=Q() if assignment.scope=="COMPANY" else Q(branch_id__in=branch_ids)
            if assignment.scope=="BRANCHES" and user.branch_id in branch_ids: condition |= Q(branch__isnull=True)
            for field in ("department_id","team_id"):
                condition &= Q(**{field:getattr(assignment.position,field)}) | Q(**{field+'__isnull':True})
            eligible |= condition
        queryset=queryset.filter(eligible)
        position_audience = Q(audience_position_ids=[])
        if primary:
            position_audience |= Q(audience_position_ids__contains=[primary.pk])
        for assignment in PositionScope.assignments(user):
            if assignment.scope == 'COMPANY' or assignment.branches.filter(pk=user.branch_id, company_id=user.company_id, is_active=True).exists():
                position_audience |= Q(audience_position_ids__contains=[assignment.position_id])
        branch_id = getattr(cls.starting_branch(user), 'pk', None)
        queryset = queryset.filter(Q(audience_branch_ids=[]) | Q(audience_branch_ids__contains=[branch_id]))
        if not history:
            queryset = queryset.filter(lifecycle_status='PUBLISHED', is_active=True)
            from core.data_classification import DataClassification
            from core.classification_policy import ClassificationPolicy
            denied = [classification for classification in DataClassification.SENSITIVE
                      if not ClassificationPolicy.can_disclose(user=user, classification=classification)]
            restricted = queryset.filter(share_confidential=False, fields__classification__in=denied).values('pk')
            queryset = queryset.exclude(pk__in=restricted)
        return queryset.filter(Q(audience_roles=[]) | Q(audience_roles__contains=[user.role])).filter(Q(audience_user_ids=[]) | Q(audience_user_ids__contains=[str(user.pk)])).filter(position_audience)

    @classmethod
    def shared_templates(cls, user):
        from .models import FormTemplate
        return cls.templates(user, FormTemplate.objects.filter(entry_visibility='AUDIENCE'), history=True)

    @classmethod
    def shared_confidential(cls, user, submission):
        return ((submission.status not in {'DRAFT', 'RETURNED', 'CANCELLED'} or submission.submitted_by_id == user.pk)
                and submission.company_id == user.company_id and submission.template.share_confidential
                and cls.shared_templates(user).filter(pk=submission.template_id).exists())

    @classmethod
    def eligible(cls, user, template):
        return cls.templates(user, type(template).objects.filter(pk=template.pk)).exists()
