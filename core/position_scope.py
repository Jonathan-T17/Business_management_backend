"""Primary and additional positions contribute explicitly scoped access."""
from django.db.models import Q, F

# These capabilities have explicit scope-aware operational consumers below.
BRANCH_CAPABILITIES = {
    "USE_FORMS", "SUBMIT_FORMS", "VIEW_FORM_SUBMISSIONS", "REVIEW_SUBMISSIONS",
    "VIEW_ALL_REPORTS", "VIEW_COMPANY_ANALYTICS",
    "VIEW_ALL_EMPLOYEES",
}

class PositionScope:
    @staticmethod
    def primary_position(user):
        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(user):
            return None
        profile = getattr(user, "employee_profile", None)
        if not profile or profile.company_id != user.company_id or profile.status != "ACTIVE" or not profile.position_id:
            return None
        position = profile.position
        if not position.is_active or position.company_id != user.company_id:
            return None
        if position.primary_scope == "BRANCH" and (
            not position.branch_id or not position.branch.is_active or position.branch.company_id != user.company_id
        ):
            return None
        return position

    @classmethod
    def primary_capabilities(cls, user, *, company_only=False):
        position = cls.primary_position(user)
        if position is None or (company_only and position.primary_scope != "COMPANY"):
            return set()
        caps = set(position.capability_grants.filter(company_id=user.company_id, is_active=True).values_list("capability", flat=True))
        if position.primary_scope == "COMPANY":
            return caps
        return caps & BRANCH_CAPABILITIES if position.primary_scope == "BRANCH" else set()

    @staticmethod
    def assignments(user):
        from organizations.models import EmployeePositionAssignment
        from core.capability_service import CapabilityService
        qs = EmployeePositionAssignment.objects.all()
        if not CapabilityService.is_tenant_identity(user):
            return qs.none()
        profile=getattr(user,"employee_profile",None)
        if not profile or profile.company_id!=user.company_id or profile.status!="ACTIVE":
            return qs.none()
        return qs.filter(company_id=user.company_id, employee__company_id=user.company_id,
            employee__user=user,employee__status="ACTIVE",position__company_id=user.company_id,
            position__is_active=True,is_active=True).exclude(employee__position_id=F("position_id"))

    @classmethod
    def capabilities(cls,user, *, company_only=False):
        result=set()
        for assignment in cls.assignments(user).select_related("position").prefetch_related("position__capability_grants", "branches"):
            caps={g.capability for g in assignment.position.capability_grants.all() if g.is_active and g.company_id==user.company_id}
            if assignment.scope=="COMPANY": result.update(caps)
            elif not company_only and assignment.scope=="BRANCHES" and any(b.is_active and b.company_id==user.company_id for b in assignment.branches.all()):
                result.update(caps & BRANCH_CAPABILITIES)
        return result

    @classmethod
    def branches_for(cls,user,capability):
        if capability not in BRANCH_CAPABILITIES: return set()
        branches = set(cls.assignments(user).filter(scope="BRANCHES",position__capability_grants__capability=capability,
            position__capability_grants__is_active=True,position__capability_grants__company_id=user.company_id,
            branches__company_id=user.company_id,branches__is_active=True).values_list("branches__id",flat=True))
        primary = cls.primary_position(user)
        if primary and primary.primary_scope == "BRANCH" and capability in cls.primary_capabilities(user):
            branches.add(primary.branch_id)
        return branches

    @classmethod
    def scope_q(cls,user,capability,field="branch_id"):
        from core.capability_service import CapabilityService
        if CapabilityService.has_company(user,capability): return Q()
        return Q(**{field+"__in":cls.branches_for(user,capability)})

    @classmethod
    def position_users(cls, *, company, position, branch_id=None):
        from users.models import User
        from organizations.models import EmployeePositionAssignment
        if position.company_id != company.pk or not position.is_active:
            return User.objects.none()
        extra=EmployeePositionAssignment.objects.filter(company=company,employee__company=company,
            employee__status="ACTIVE",position=position,position__company=company,position__is_active=True,is_active=True)
        extra=extra.filter(Q(scope="COMPANY") | Q(scope="BRANCHES",branches__id=branch_id,branches__company=company,branches__is_active=True)) if branch_id else extra.filter(scope="COMPANY")
        primary = Q(employee_profile__position=position, employee_profile__status="ACTIVE",
                    employee_profile__position__is_active=True, employee_profile__company=company)
        if position.primary_scope == "BRANCH":
            primary &= Q(employee_profile__position__branch_id=branch_id,
                         employee_profile__position__branch__company=company,
                         employee_profile__position__branch__is_active=True) if branch_id else Q(pk__in=[])
        return User.objects.filter(company=company,is_active=True,is_deleted=False,is_superuser=False).exclude(role="SUPERUSER").filter(
            primary |
            Q(employee_profile__in=extra.values("employee_id"))).distinct()

    @classmethod
    def recipient_current(cls,recipient):
        step=recipient.step
        snapshot=step.routing_snapshot or {}
        definition=step.definition_step
        kind=snapshot.get("recipient_type") or getattr(definition,"recipient_type",None)
        if kind!="POSITION": return True
        position_id=snapshot.get("recipient_position_id") or getattr(definition,"recipient_position_id",None)
        from organizations.models import Position
        position=Position.objects.filter(pk=position_id,company_id=step.workflow_instance.company_id,is_active=True).first()
        if not position: return False
        return cls.position_users(company=step.workflow_instance.company,position=position,
            branch_id=getattr(step.workflow_instance.content_object,"branch_id",None)).filter(pk=recipient.user_id).exists()

    @classmethod
    def current_recipients(cls,queryset):
        ids=[r.pk for r in queryset.select_related("step__definition_step","step__workflow_instance__content_type") if cls.recipient_current(r)]
        return queryset.filter(pk__in=ids)
