"""Additional-position grants retain their scope; they are never flattened into admin access."""
from django.db.models import Q, F

# These capabilities have explicit scope-aware operational consumers below.
BRANCH_CAPABILITIES = {
    "USE_FORMS", "SUBMIT_FORMS", "VIEW_FORM_SUBMISSIONS", "REVIEW_SUBMISSIONS",
    "VIEW_ALL_REPORTS", "VIEW_COMPANY_ANALYTICS",
}

class PositionScope:
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
        return set(cls.assignments(user).filter(scope="BRANCHES",position__capability_grants__capability=capability,
            position__capability_grants__is_active=True,position__capability_grants__company_id=user.company_id,
            branches__company_id=user.company_id,branches__is_active=True).values_list("branches__id",flat=True))

    @classmethod
    def scope_q(cls,user,capability,field="branch_id"):
        from core.capability_service import CapabilityService
        if CapabilityService.has_company(user,capability): return Q()
        return Q(**{field+"__in":cls.branches_for(user,capability)})

    @classmethod
    def position_users(cls, *, company, position, branch_id=None):
        from users.models import User
        from organizations.models import EmployeePositionAssignment
        extra=EmployeePositionAssignment.objects.filter(company=company,employee__company=company,
            employee__status="ACTIVE",position=position,position__company=company,position__is_active=True,is_active=True)
        extra=extra.filter(Q(scope="COMPANY") | Q(scope="BRANCHES",branches__id=branch_id,branches__company=company,branches__is_active=True)) if branch_id else extra.filter(scope="COMPANY")
        return User.objects.filter(company=company,is_active=True,is_deleted=False,is_superuser=False).exclude(role="SUPERUSER").filter(
            Q(employee_profile__position=position,employee_profile__status="ACTIVE",employee_profile__position__is_active=True) |
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
