from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from companies.models import Branch
from core.position_scope import BRANCH_CAPABILITIES
from company_setup.capability_policy import SetupCapabilityPolicy
from security.services import create_audit_log
from .models import EmployeePositionAssignment, EmployeeProfile, Position
from .permissions import CanManageOrganization

class PositionAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.user.full_name", read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True)
    class Meta:
        model = EmployeePositionAssignment
        fields = ("id","employee","employee_name","position","position_title","scope","branches","is_active","created_at")
        read_only_fields = ("created_at",)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        user=getattr(self.context.get("request"),"user",None)
        company_id=getattr(user,"company_id",None)
        self.fields["employee"].queryset=EmployeeProfile.objects.filter(company_id=company_id,user__company_id=company_id)
        self.fields["position"].queryset=Position.objects.filter(company_id=company_id)
        self.fields["branches"].child_relation.queryset=Branch.objects.filter(company_id=company_id)

    def validate(self,attrs):
        def value(key): return attrs.get(key,getattr(self.instance,key,None))
        employee,position=value("employee"),value("position")
        active=attrs.get("is_active",getattr(self.instance,"is_active",True))
        company_id=self.context["request"].user.company_id
        if employee.company_id!=company_id or employee.user.company_id!=company_id or position.company_id!=company_id:
            raise serializers.ValidationError("Employee and position must belong to your company.")
        branches=attrs.get("branches",list(self.instance.branches.all()) if self.instance else [])
        if any(b.company_id!=company_id for b in branches):
            raise serializers.ValidationError({"branches":"Choose locations in your company."})
        if not active: return attrs
        if employee.status!="ACTIVE" or not position.is_active:
            raise serializers.ValidationError("Choose an active employee and position.")
        if employee.position_id==position.pk:
            raise serializers.ValidationError("This is already the employee's primary position. Additional assignments must use another position.")
        branches=attrs.get("branches",list(self.instance.branches.all()) if self.instance else [])
        if value("scope")=="BRANCHES" and (not branches or any(not b.is_active for b in branches)):
            raise serializers.ValidationError({"branches":"Choose at least one active company location."})
        if value("scope")=="COMPANY" and branches:
            raise serializers.ValidationError({"branches":"Company-wide assignments must not contain a location restriction."})
        caps=set(position.capability_grants.filter(company=employee.company,is_active=True).values_list("capability",flat=True))
        if value("scope")=="BRANCHES" and caps-BRANCH_CAPABILITIES:
            raise serializers.ValidationError({"position":"This position contains company-wide or unsupported permissions. Create an operational position using: "+", ".join(code.replace("_", " ").lower() for code in sorted(BRANCH_CAPABILITIES))})
        SetupCapabilityPolicy.validate_preset(actor=self.context["request"].user,capabilities=list(caps))
        return attrs

class PositionAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class=PositionAssignmentSerializer
    permission_classes=[IsAuthenticated,CanManageOrganization]
    http_method_names=["get","post","patch","head","options"]
    def get_queryset(self):
        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(self.request.user): return EmployeePositionAssignment.objects.none()
        qs=EmployeePositionAssignment.objects.filter(company=self.request.user.company,employee__company=self.request.user.company,position__company=self.request.user.company).select_related("employee__user","position").prefetch_related("branches")
        employee=self.request.query_params.get("employee")
        return qs.filter(employee_id=employee) if employee and employee.isdigit() else qs
    @transaction.atomic
    def perform_create(self,serializer):
        assignment=serializer.save(company=self.request.user.company,created_by=self.request.user)
        self.audit(assignment)
    @transaction.atomic
    def perform_update(self,serializer):
        self.audit(serializer.save())
    def audit(self,assignment):
        create_audit_log(user=self.request.user,company=self.request.user.company,request=self.request,action="SECURITY",
            description=f"Position assignment updated: {assignment.position.title}; scope {assignment.scope}; active {assignment.is_active}.",obj=assignment)
