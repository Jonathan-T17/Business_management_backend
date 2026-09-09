from dataclasses import dataclass
from companies.models import Branch
from organizations.models import Department, EmployeeProfile, Position
from .models import (
    ApprovalRoute, NotificationPolicy, OfficialRecordPolicy,
    ReportingProcess, RequestTypeDefinition, RolePreset,
)

@dataclass(frozen=True)
class Check:
    code: str
    severity: str
    passed: bool
    message: str
    destination: str
    blocking: bool = False

class SetupReadinessService:
    """
    Server-derived readiness. Client-provided completed_steps never decides
    whether a company is operationally ready.
    """
    @classmethod
    def checks(cls, company):
        checks = []
        profile_fields = ("official_name", "country", "timezone", "default_currency")
        missing = [f for f in profile_fields if not getattr(company, f, None)]
        checks.append(Check(
            "COMPANY_PROFILE", "ERROR" if missing else "INFO", not missing,
            "Complete company profile." if missing else "Company profile complete.",
            "/settings/company", blocking=bool(missing),
        ))

        branches = Branch.objects.filter(company=company, is_active=True).exists()
        checks.append(Check("ACTIVE_BRANCH", "WARNING", branches,
                            "Add an active headquarters or branch." if not branches else "Active branch configured.",
                            "/settings/organization"))

        departments = Department.objects.filter(company=company, is_active=True).exists()
        checks.append(Check("ACTIVE_DEPARTMENT", "WARNING", departments,
                            "Add an active department." if not departments else "Department configured.",
                            "/settings/organization"))

        positions = Position.objects.filter(company=company).exists()
        checks.append(Check("POSITIONS", "WARNING", positions,
                            "Create at least one position." if not positions else "Positions configured.",
                            "/settings/organization"))

        active_employees = EmployeeProfile.objects.filter(company=company, status="ACTIVE")
        without_position = active_employees.filter(position__isnull=True).count()
        checks.append(Check("EMPLOYEE_POSITIONS", "WARNING", without_position == 0,
                            f"{without_position} active employees have no position." if without_position else "Active employees have positions.",
                            "/settings/employees"))

        presets = RolePreset.objects.filter(company=company, is_active=True).exists() or RolePreset.objects.filter(company__isnull=True, is_system=True, is_active=True).exists()
        checks.append(Check("ROLE_PRESETS", "ERROR" if not presets else "INFO", presets,
                            "Configure at least one safe role preset." if not presets else "Role presets available.",
                            "/settings/permissions", blocking=not presets))

        return checks

    @classmethod
    def evaluate(cls, company):
        checks = cls.checks(company)
        blocking = [c for c in checks if c.blocking and not c.passed]
        warnings = [c for c in checks if not c.passed and not c.blocking]
        passed = sum(1 for c in checks if c.passed)
        score = round((passed / len(checks)) * 100) if checks else 100
        return {
            "ready": not blocking,
            "score": score,
            "status": "READY" if not blocking else "BLOCKED",
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
            "checks": [c.__dict__ for c in checks],
        }
