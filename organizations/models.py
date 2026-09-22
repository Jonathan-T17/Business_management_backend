from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.capabilities import Capabilities

User = settings.AUTH_USER_MODEL


# ============================================================
# Department
# ============================================================

class Department(models.Model):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="departments",
    )

    # NULL = Head Office / company-level department
    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="departments",
    )

    name = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        null=True,
    )

    manager = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_departments",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_departments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "branch", "name"],
                name="unique_department_per_company_branch",
            ),
        ]

        indexes = [
            models.Index(
                fields=["company", "branch", "is_active"],
            ),
        ]

    def clean(self):
        if self.branch and self.branch.company_id != self.company_id:
            raise ValidationError(
                "Department branch must belong to the same company."
            )

        if self.manager:
            if self.manager.company_id != self.company_id:
                raise ValidationError(
                    "Department manager must belong to the same company."
                )

            # Head-office department -> manager must be head-office staff.
            if self.branch_id is None and self.manager.branch_id is not None:
                raise ValidationError(
                    "A head-office department must have a head-office manager."
                )

            # Branch department -> manager must belong to that branch.
            if (
                self.branch_id is not None
                and self.manager.branch_id != self.branch_id
            ):
                raise ValidationError(
                    "Department manager must belong to the department branch."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        if self.branch:
            return f"{self.branch.name} / {self.name}"

        return f"{self.company.name} / Head Office / {self.name}"


# ============================================================
# Team
# ============================================================

class Team(models.Model):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="teams",
    )

    # NULL = Head Office team
    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="teams",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="teams",
    )

    name = models.CharField(max_length=200)

    description = models.TextField(
        blank=True,
        null=True,
    )

    leader = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="led_teams",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_teams",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_team_per_department",
            ),
        ]

        indexes = [
            models.Index(
                fields=["company", "department", "is_active"],
            ),
        ]

    def clean(self):
        if self.department.company_id != self.company_id:
            raise ValidationError(
                "Team and department must belong to the same company."
            )

        if self.department.branch_id != self.branch_id:
            raise ValidationError(
                "Team and department must belong to the same organizational level."
            )

        if self.leader:
            if self.leader.company_id != self.company_id:
                raise ValidationError(
                    "Team leader must belong to the same company."
                )

            if self.branch_id is None:
                if self.leader.branch_id is not None:
                    raise ValidationError(
                        "A head-office team must have a head-office leader."
                    )
            elif self.leader.branch_id != self.branch_id:
                raise ValidationError(
                    "Team leader must belong to the same branch."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.department.name} / {self.name}"


# ============================================================
# Position
# ============================================================

class Position(models.Model):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="positions",
    )

    branch = models.ForeignKey("companies.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="positions")
    department = models.ForeignKey("organizations.Department", null=True, blank=True, on_delete=models.PROTECT, related_name="positions")
    team = models.ForeignKey("organizations.Team", null=True, blank=True, on_delete=models.PROTECT, related_name="positions")
    reports_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reporting_positions")

    title = models.CharField(max_length=200)

    description = models.TextField(blank=True)

    salary_grade = models.CharField(
        max_length=50,
        blank=True,
    )

    is_management = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "title"],
                name="unique_position_per_company",
            ),
        ]

    def __str__(self):
        return self.title


# ============================================================
# Employee Profile
# ============================================================

class EmployeeProfile(models.Model):

    EMPLOYMENT_TYPES = (
        ("FULL_TIME", "Full Time"),
        ("PART_TIME", "Part Time"),
        ("CONTRACT", "Contract"),
        ("INTERN", "Intern"),
    )

    STATUS = (
        ("ACTIVE", "Active"),
        ("ON_LEAVE", "On Leave"),
        ("SUSPENDED", "Suspended"),
        ("TERMINATED", "Terminated"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )

    employee_id = models.CharField(
        max_length=50,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employees",
    )

    # NULL = Head Office employee
    branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )

    team = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )

    manager = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
    )

    position = models.ForeignKey(
        Position,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )

    employment_type = models.CharField(
        max_length=30,
        choices=EMPLOYMENT_TYPES,
        default="FULL_TIME",
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS,
        default="ACTIVE",
    )

    hire_date = models.DateField(
        default=timezone.now,
    )

    termination_date = models.DateField(
        null=True,
        blank=True,
    )

    termination_reason = models.TextField(
        blank=True,
    )

    terminated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="terminated_employees",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    office_location = models.CharField(
        max_length=255,
        blank=True,
    )

    emergency_contact = models.CharField(
        max_length=255,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_id"]
        constraints = [models.UniqueConstraint(fields=["company", "employee_id"], name="unique_employee_id_per_company")]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "department",
                    "team",
                    "status",
                ]
            ),
        ]

    def clean(self):
        if self.user.company_id != self.company_id:
            raise ValidationError(
                "Employee user must belong to the same company."
            )

        if self.branch and self.branch.company_id != self.company_id:
            raise ValidationError(
                "Employee branch must belong to the same company."
            )

        if self.department:
            if self.department.company_id != self.company_id:
                raise ValidationError(
                    "Employee department must belong to the same company."
                )

            if self.department.branch_id not in (None, self.branch_id):
                raise ValidationError(
                    "Employee department must belong to the same organizational level."
                )

        if self.team:
            if self.team.company_id != self.company_id:
                raise ValidationError(
                    "Employee team must belong to the same company."
                )

            if self.team.branch_id != self.branch_id:
                raise ValidationError(
                    "Employee team must belong to the same branch/head-office level."
                )

            if self.department_id != self.team.department_id:
                raise ValidationError(
                    "Employee team must belong to the selected department."
                )

        if self.manager:
            if self.manager.company_id != self.company_id:
                raise ValidationError(
                    "Employee manager must belong to the same company."
                )

            if self.manager_id == self.user_id:
                raise ValidationError(
                    "An employee cannot manage themselves."
                )

            if self.branch_id != self.manager.branch_id:
                raise ValidationError(
                    "Employee manager must belong to the same organizational level."
                )

        if self.position:
            if self.position.company_id != self.company_id:
                raise ValidationError(
                    "Employee position must belong to the same company."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        full_name = getattr(self.user, "full_name", None)

        if not full_name:
            full_name = self.user.get_username()

        return f"{self.employee_id} - {full_name}"


# ============================================================
# User Capability Grant
# ============================================================

class UserCapabilityGrant(models.Model):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="user_capability_grants",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="capability_grants",
    )

    capability = models.CharField(
        max_length=100,
        choices=Capabilities.choices(),
    )

    granted_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="capabilities_granted",
    )

    reason = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    revoked_at = models.DateTimeField(null=True, blank=True)

    revoked_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="capabilities_revoked",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user", "capability"],
                name="unique_company_user_capability",
            )
        ]

        indexes = [
            models.Index(
                fields=["company", "user", "is_active"]
            )
        ]

    def __str__(self):
        return f"{self.user.email}: {self.capability}"


# ============================================================
# Position Capability Grant
# ============================================================

class PositionCapabilityGrant(models.Model):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="position_capability_grants",
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name="capability_grants",
    )

    capability = models.CharField(
        max_length=100,
        choices=Capabilities.choices(),
    )

    granted_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="position_capabilities_granted",
    )

    reason = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "position", "capability"],
                name="unique_company_position_capability",
            )
        ]

    def __str__(self):
        return f"{self.position.title}: {self.capability}"


# ============================================================
# Employee Compensation
# ============================================================

class EmployeeCompensation(models.Model):

    CURRENCY_CHOICES = (
        ("RWF", "Rwandan Franc"),
        ("USD", "US Dollar"),
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
    )

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="compensation_records",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employee_compensations",
    )

    base_salary = models.DecimalField(max_digits=15, decimal_places=2)

    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default="RWF",
    )

    housing_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    transport_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    other_allowance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )

    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_compensation_records",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_from"]
        indexes = [
            models.Index(
                fields=["company", "employee", "is_current"]
            )
        ]

    @property
    def gross_fixed_compensation(self):
        return (
            self.base_salary
            + self.housing_allowance
            + self.transport_allowance
            + self.other_allowance
        )

    def __str__(self):
        return (
            f"{self.employee.employee_id} "
            f"{self.currency} {self.base_salary}"
        )


# ============================================================
# Employee Delegation
# ============================================================

class EmployeeDelegation(models.Model):

    STATUS_CHOICES = (
        ("SCHEDULED", "Scheduled"),
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employee_delegations",
    )

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="delegations_given",
    )

    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="delegations_received",
    )

    permissions = models.JSONField(
        default=list,
        blank=True,
    )

    reason = models.TextField(
        blank=True,
    )

    starts_at = models.DateTimeField()

    ends_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SCHEDULED",
    )

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_delegations",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=[
                    "company",
                    "status",
                    "starts_at",
                    "ends_at",
                ]
            )
        ]

    def __str__(self):
        return (
            f"{self.from_user.email} → "
            f"{self.to_user.email}"
        )


class EmployeeReplacement(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employee_replacements",
    )

    outgoing_employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="replacement_history",
    )

    incoming_employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.PROTECT,
        related_name="replaced_employees",
    )

    transfer_open_tasks = models.BooleanField(
        default=True,
    )

    transfer_project_memberships = models.BooleanField(
        default=True,
    )

    transfer_team_leadership = models.BooleanField(
        default=False,
    )

    transfer_department_management = models.BooleanField(
        default=False,
    )

    transfer_branch_management = models.BooleanField(
        default=False,
    )

    reason = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    performed_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="employee_replacements_performed",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]


# ============================================================
# Employee Transfer
# ============================================================

class EmployeeTransfer(models.Model):

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="transfers",
    )

    old_branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    new_branch = models.ForeignKey(
        "companies.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    old_department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    new_department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    old_team = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    new_team = models.ForeignKey(
        Team,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    approved_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="approved_transfers",
    )

    reason = models.TextField()

    effective_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["employee", "effective_date"],
            ),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} transfer"


# ============================================================
# Employee Notes
# ============================================================

class EmployeeNote(models.Model):

    employee = models.ForeignKey(
        EmployeeProfile,
        on_delete=models.CASCADE,
        related_name="notes_history",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employee_notes",
    )

    note = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note - {self.employee.employee_id}"


class EmployeePositionAssignment(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="position_assignments")
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="assignments")
    scope = models.CharField(max_length=20, choices=[("COMPANY", "Company-wide"), ("BRANCHES", "Selected locations")])
    branches = models.ManyToManyField("companies.Branch", blank=True, related_name="position_assignments")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "position"], name="unique_employee_additional_position")]
