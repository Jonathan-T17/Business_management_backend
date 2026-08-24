from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


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
        unique=True,
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

            if self.department.branch_id != self.branch_id:
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