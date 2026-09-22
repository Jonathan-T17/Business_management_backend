from rest_framework import serializers

from .models import (
    Department,
    Team,
    Position,
    EmployeeProfile,
    EmployeeTransfer,
    EmployeeNote,
    EmployeeDelegation,
    EmployeeReplacement,
    EmployeeCompensation,
    UserCapabilityGrant,
    PositionCapabilityGrant,
)


class DepartmentSerializer(serializers.ModelSerializer):

    manager_name = serializers.CharField(
        source="manager.full_name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    class Meta:
        model = Department

        fields = (
            "id",
            "company",
            "branch",
            "branch_name",
            "name",
            "description",
            "manager",
            "manager_name",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        branch = attrs.get("branch")
        manager = attrs.get("manager")

        if branch and branch.company_id != user.company_id:
            raise serializers.ValidationError({
                "branch": "Branch does not belong to your company."
            })

        if manager:
            if manager.company_id != user.company_id:
                raise serializers.ValidationError({
                    "manager": "Manager does not belong to your company."
                })

            if branch and manager.branch_id != branch.id:
                raise serializers.ValidationError({
                    "manager": "Manager must belong to the selected branch."
                })

        return attrs


class EmployeeDelegationSerializer(serializers.ModelSerializer):

    from_user_name = serializers.CharField(
        source="from_user.full_name",
        read_only=True,
    )

    to_user_name = serializers.CharField(
        source="to_user.full_name",
        read_only=True,
    )

    class Meta:
        model = EmployeeDelegation

        fields = ('id', 'from_user_name', 'to_user_name', 'permissions', 'reason', 'starts_at', 'ends_at', 'status', 'created_at', 'company', 'from_user', 'to_user', 'created_by')

        read_only_fields = (
            "company",
            "created_by",
            "status",
            "created_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        from_user = attrs.get("from_user")
        to_user = attrs.get("to_user")

        if (
            from_user.company_id != request.user.company_id
            or to_user.company_id != request.user.company_id
        ):
            raise serializers.ValidationError(
                "Delegation users must belong to your company."
            )

        return attrs


class EmployeeReplacementSerializer(serializers.ModelSerializer):

    outgoing_name = serializers.CharField(
        source="outgoing_employee.user.full_name",
        read_only=True,
    )

    incoming_name = serializers.CharField(
        source="incoming_employee.user.full_name",
        read_only=True,
    )

    class Meta:
        model = EmployeeReplacement

        fields = ('id', 'outgoing_name', 'incoming_name', 'transfer_open_tasks', 'transfer_project_memberships', 'transfer_team_leadership', 'transfer_department_management', 'transfer_branch_management', 'reason', 'status', 'created_at', 'completed_at', 'company', 'outgoing_employee', 'incoming_employee', 'performed_by')

        read_only_fields = (
            "company",
            "performed_by",
            "status",
            "created_at",
            "completed_at",
        )


class EmployeeCompensationSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.user.full_name",
        read_only=True,
    )
    employee_email = serializers.CharField(
        source="employee.user.email",
        read_only=True,
    )
    employee_id_display = serializers.CharField(
        source="employee.employee_id",
        read_only=True,
    )
    gross_fixed_compensation = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = EmployeeCompensation
        fields = (
            "id", "employee", "employee_name", "employee_email",
            "employee_id_display", "company", "base_salary", "currency",
            "housing_allowance", "transport_allowance", "other_allowance",
            "gross_fixed_compensation", "effective_from", "effective_to",
            "notes", "is_current", "created_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "company", "is_current", "created_by", "created_at", "updated_at",
        )


class UserCapabilityGrantSerializer(serializers.ModelSerializer):

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserCapabilityGrant
        fields = (
            "id", "company", "user", "user_name", "user_email", "capability",
            "reason", "is_active", "granted_by", "created_at", "revoked_at",
            "revoked_by",
        )
        read_only_fields = (
            "company", "is_active", "granted_by", "created_at", "revoked_at",
            "revoked_by",
        )


class PositionCapabilityGrantSerializer(serializers.ModelSerializer):

    position_name = serializers.CharField(
        source="position.title",
        read_only=True,
    )

    class Meta:
        model = PositionCapabilityGrant
        fields = (
            "id", "company", "position", "position_name", "capability",
            "reason", "is_active", "granted_by", "created_at",
        )
        read_only_fields = (
            "company", "is_active", "granted_by", "created_at",
        )


class TeamSerializer(serializers.ModelSerializer):

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    leader_name = serializers.CharField(
        source="leader.full_name",
        read_only=True,
    )

    class Meta:
        model = Team

        fields = (
            "id",
            "company",
            "branch",
            "department",
            "department_name",
            "name",
            "description",
            "leader",
            "leader_name",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        department = attrs.get("department")
        branch = attrs.get("branch")
        leader = attrs.get("leader")

        if branch and branch.company_id != user.company_id:
            raise serializers.ValidationError({
                "branch": "Branch does not belong to your company."
            })

        if department:
            if department.company_id != user.company_id:
                raise serializers.ValidationError({
                    "department":
                        "Department does not belong to your company."
                })

            if branch and department.branch_id != branch.id:
                raise serializers.ValidationError({
                    "department":
                        "Department must belong to the selected branch."
                })

        if leader:
            if leader.company_id != user.company_id:
                raise serializers.ValidationError({
                    "leader":
                        "Team leader does not belong to your company."
                })

            if branch and leader.branch_id != branch.id:
                raise serializers.ValidationError({
                    "leader":
                        "Team leader must belong to the selected branch."
                })

        return attrs


class PositionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Position

        fields = (
            "id",
            "company",
            "title",
            "branch", "department", "team", "reports_to",
            "description",
            "salary_grade",
            "is_management",
            "is_active",
        )

        read_only_fields = (
            "company",
        )


    def validate(self, attrs):
        company = self.context["request"].user.company
        values = {key: attrs.get(key, getattr(self.instance, key, None))
                  for key in ("branch", "department", "team", "reports_to")}
        for key, obj in values.items():
            if obj and (obj.company_id != company.pk or not obj.is_active):
                raise serializers.ValidationError({key: "Choose an active item in your company."})
        branch, department, team = (values[k] for k in ("branch", "department", "team"))
        if department and department.branch_id not in (None, getattr(branch, "pk", None)):
            raise serializers.ValidationError({"department": "This department belongs to another location."})
        if team and (team.department_id != getattr(department, "pk", None) or team.branch_id != getattr(branch, "pk", None)):
            raise serializers.ValidationError({"team": "Choose a team within this department and location."})
        parent, seen = values["reports_to"], set()
        while parent:
            if parent.pk in seen or (self.instance and parent.pk == self.instance.pk):
                raise serializers.ValidationError({"reports_to": "Reporting relationships cannot form a loop."})
            seen.add(parent.pk)
            parent = parent.reports_to
        return attrs


class EmployeeProfileSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="user.full_name",
        read_only=True,
    )

    email = serializers.CharField(
        source="user.email",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="company.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    team_name = serializers.CharField(
        source="team.name",
        read_only=True,
    )

    manager_name = serializers.CharField(
        source="manager.full_name",
        read_only=True,
    )

    position_name = serializers.CharField(
        source="position.title",
        read_only=True,
    )

    class Meta:
        model = EmployeeProfile

        fields = ('id', 'employee_name', 'email', 'company_name', 'branch_name', 'department_name', 'team_name', 'manager_name', 'position_name', 'employee_id', 'employment_type', 'status', 'hire_date', 'termination_date', 'termination_reason', 'phone', 'office_location', 'emergency_contact', 'notes', 'created_at', 'updated_at', 'user', 'company', 'branch', 'department', 'team', 'manager', 'position', 'terminated_by')

        read_only_fields = (
            "company",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        company = user.company

        selected_user = attrs.get("user")
        branch = attrs.get("branch")
        department = attrs.get("department")
        team = attrs.get("team")
        manager = attrs.get("manager")
        position = attrs.get("position")

        if selected_user:
            if selected_user.company_id != company.id:
                raise serializers.ValidationError({
                    "user":
                        "User does not belong to your company."
                })

        if branch:
            if branch.company_id != company.id:
                raise serializers.ValidationError({
                    "branch":
                        "Branch does not belong to your company."
                })

        if department:
            if department.company_id != company.id:
                raise serializers.ValidationError({
                    "department":
                        "Department does not belong to your company."
                })

            if branch and department.branch_id != branch.id:
                raise serializers.ValidationError({
                    "department":
                        "Department must belong to the selected branch."
                })

        if team:
            if team.company_id != company.id:
                raise serializers.ValidationError({
                    "team":
                        "Team does not belong to your company."
                })

            if department and team.department_id != department.id:
                raise serializers.ValidationError({
                    "team":
                        "Team must belong to the selected department."
                })

            if branch and team.branch_id != branch.id:
                raise serializers.ValidationError({
                    "team":
                        "Team must belong to the selected branch."
                })

        if manager:
            if manager.company_id != company.id:
                raise serializers.ValidationError({
                    "manager":
                        "Manager does not belong to your company."
                })

            if branch and manager.branch_id != branch.id:
                raise serializers.ValidationError({
                    "manager":
                        "Manager must belong to the selected branch."
                })

        if position:
            if position.company_id != company.id:
                raise serializers.ValidationError({
                    "position":
                        "Position does not belong to your company."
                })

        return attrs


class EmployeeTransferSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.user.full_name",
        read_only=True,
    )

    approved_by_name = serializers.CharField(
        source="approved_by.full_name",
        read_only=True,
    )

    class Meta:
        model = EmployeeTransfer

        fields = ('id', 'employee_name', 'approved_by_name', 'reason', 'effective_date', 'created_at', 'employee', 'old_branch', 'new_branch', 'old_department', 'new_department', 'old_team', 'new_team', 'approved_by')

        read_only_fields = (
            "approved_by",
            "created_at",
            "old_branch",
            "old_department",
            "old_team",
        )


class EmployeeNoteSerializer(serializers.ModelSerializer):

    author_name = serializers.CharField(
        source="author.full_name",
        read_only=True,
    )

    class Meta:
        model = EmployeeNote

        fields = ('id', 'author_name', 'note', 'created_at', 'employee', 'author')

        read_only_fields = (
            "author",
            "created_at",
        )

    def validate_employee(self, employee):
        request = self.context["request"]
        user = request.user

        from core.capability_service import CapabilityService
        if not CapabilityService.is_tenant_identity(user) or employee.company_id != user.company_id:
            raise serializers.ValidationError(
                "Employee does not belong to your company."
            )

        return employee